use std::env;
use std::fs;
use std::time::Instant;

const MAGIC_IN: &[u8; 8] = b"LDRUST01";
const MAGIC_OUT: &[u8; 8] = b"LDRSOUT1";

struct Reader {
    data: Vec<u8>,
    pos: usize,
}
impl Reader {
    fn new(data: Vec<u8>) -> Self {
        Self { data, pos: 0 }
    }
    fn bytes(&mut self, n: usize) -> Vec<u8> {
        let v = self.data[self.pos..self.pos + n].to_vec();
        self.pos += n;
        v
    }
    fn u8(&mut self) -> u8 {
        let v = self.data[self.pos];
        self.pos += 1;
        v
    }
    fn u32(&mut self) -> u32 {
        let b = self.bytes(4);
        u32::from_le_bytes(b.try_into().unwrap())
    }
    fn u64(&mut self) -> u64 {
        let b = self.bytes(8);
        u64::from_le_bytes(b.try_into().unwrap())
    }
    fn f64(&mut self) -> f64 {
        let b = self.bytes(8);
        f64::from_le_bytes(b.try_into().unwrap())
    }
    fn vec_u32(&mut self, n: usize) -> Vec<u32> {
        (0..n).map(|_| self.u32()).collect()
    }
    fn vec_u64(&mut self, n: usize) -> Vec<u64> {
        (0..n).map(|_| self.u64()).collect()
    }
    fn vec_f64(&mut self, n: usize) -> Vec<f64> {
        (0..n).map(|_| self.f64()).collect()
    }
}
fn put_u32(out: &mut Vec<u8>, x: u32) {
    out.extend_from_slice(&x.to_le_bytes());
}
fn put_u64(out: &mut Vec<u8>, x: u64) {
    out.extend_from_slice(&x.to_le_bytes());
}
fn put_f64(out: &mut Vec<u8>, x: f64) {
    out.extend_from_slice(&x.to_le_bytes());
}

struct Game {
    players: Vec<i8>,
    child_offsets: Vec<usize>,
    children: Vec<usize>,
    info_ids: Vec<usize>,
    payoffs: Vec<f64>,
    action_offsets: Vec<usize>,
    chance: Vec<f64>,
    deals: usize,
}
struct State {
    regrets: Vec<f64>,
    sums: Vec<f64>,
    visited: Vec<u8>,
    mt: [u32; 624],
    mt_index: usize,
    iterations: u64,
    node_visits: u64,
}
impl State {
    fn next_u32(&mut self) -> u32 {
        if self.mt_index >= 624 {
            const MATRIX_A: u32 = 0x9908b0df;
            const UPPER: u32 = 0x80000000;
            const LOWER: u32 = 0x7fffffff;
            for i in 0..227 {
                let y = (self.mt[i] & UPPER) | (self.mt[i + 1] & LOWER);
                self.mt[i] = self.mt[i + 397] ^ (y >> 1) ^ if y & 1 != 0 { MATRIX_A } else { 0 };
            }
            for i in 227..623 {
                let y = (self.mt[i] & UPPER) | (self.mt[i + 1] & LOWER);
                self.mt[i] = self.mt[i - 227] ^ (y >> 1) ^ if y & 1 != 0 { MATRIX_A } else { 0 };
            }
            let y = (self.mt[623] & UPPER) | (self.mt[0] & LOWER);
            self.mt[623] = self.mt[396] ^ (y >> 1) ^ if y & 1 != 0 { MATRIX_A } else { 0 };
            self.mt_index = 0;
        }
        let mut y = self.mt[self.mt_index];
        self.mt_index += 1;
        y ^= y >> 11;
        y ^= (y << 7) & 0x9d2c5680;
        y ^= (y << 15) & 0xefc60000;
        y ^= y >> 18;
        y
    }
    fn random(&mut self) -> f64 {
        let a = (self.next_u32() >> 5) as u64;
        let b = (self.next_u32() >> 6) as u64;
        ((a * 67_108_864 + b) as f64) / 9_007_199_254_740_992.0
    }
    fn choose(&mut self, weights: &[f64]) -> usize {
        let mut total = 0.0;
        let mut cum = Vec::with_capacity(weights.len());
        for &w in weights {
            total += w;
            cum.push(total);
        }
        let needle = self.random() * total;
        let mut lo = 0usize;
        let mut hi = weights.len() - 1;
        while lo < hi {
            let mid = (lo + hi) / 2;
            if needle < cum[mid] {
                hi = mid;
            } else {
                lo = mid + 1;
            }
        }
        lo
    }
}
fn traverse(game: &Game, state: &mut State, index: usize, deal: usize, updating: usize) -> f64 {
    state.node_visits += 1;
    let player = game.players[index];
    if player < 0 {
        return game.payoffs[index * game.deals + deal] * if updating == 0 { 1.0 } else { -1.0 };
    }
    let info = game.info_ids[index * game.deals + deal];
    state.visited[info] = 1;
    let start = game.action_offsets[info];
    let end = game.action_offsets[info + 1];
    let mut sum = 0.0;
    for i in start..end {
        sum += state.regrets[i].max(0.0);
    }
    let mut strategy = Vec::with_capacity(end - start);
    if sum > 0.0 {
        for i in start..end {
            strategy.push(state.regrets[i].max(0.0) / sum);
        }
    } else {
        let p = 1.0 / ((end - start) as f64);
        for _ in start..end {
            strategy.push(p);
        }
    }
    if player as usize != updating {
        let action = state.choose(&strategy);
        for (j, &p) in strategy.iter().enumerate() {
            state.sums[start + j] += p;
        }
        let child = game.children[game.child_offsets[index] + action];
        return traverse(game, state, child, deal, updating);
    }
    let mut values = Vec::with_capacity(end - start);
    for action in 0..(end - start) {
        let child = game.children[game.child_offsets[index] + action];
        values.push(traverse(game, state, child, deal, updating));
    }
    let mut value = 0.0;
    for (&p, &v) in strategy.iter().zip(values.iter()) {
        value += p * v;
    }
    for (j, &action_value) in values.iter().enumerate() {
        state.regrets[start + j] += action_value - value;
    }
    value
}
fn main() {
    let args: Vec<String> = env::args().collect();
    if args.len() != 3 {
        eprintln!("usage: leduc-kernel input.bin output.bin");
        std::process::exit(2);
    }
    let mut r = Reader::new(fs::read(&args[1]).expect("read input"));
    assert_eq!(r.bytes(8).as_slice(), MAGIC_IN);
    let iterations = r.u64() as usize;
    let n_nodes = r.u64() as usize;
    let deals = r.u64() as usize;
    let n_infos = r.u64() as usize;
    let n_edges = r.u64() as usize;
    let n_actions = r.u64() as usize;
    let mut state = State {
        iterations: r.u64(),
        node_visits: r.u64(),
        mt: [0; 624],
        mt_index: 0,
        regrets: Vec::new(),
        sums: Vec::new(),
        visited: Vec::new(),
    };
    for x in state.mt.iter_mut() {
        *x = r.u32();
    }
    state.mt_index = r.u32() as usize;
    let players: Vec<i8> = (0..n_nodes).map(|_| r.u8() as i8).collect();
    let child_offsets: Vec<usize> = r
        .vec_u64(n_nodes + 1)
        .into_iter()
        .map(|x| x as usize)
        .collect();
    let children: Vec<usize> = r.vec_u32(n_edges).into_iter().map(|x| x as usize).collect();
    let info_ids: Vec<usize> = r
        .vec_u32(n_nodes * deals)
        .into_iter()
        .map(|x| x as usize)
        .collect();
    let payoffs = r.vec_f64(n_nodes * deals);
    let chance = r.vec_f64(deals);
    let action_offsets: Vec<usize> = r
        .vec_u64(n_infos + 1)
        .into_iter()
        .map(|x| x as usize)
        .collect();
    state.regrets = r.vec_f64(n_actions);
    state.sums = r.vec_f64(n_actions);
    state.visited = r.bytes(n_infos);
    assert_eq!(r.pos, r.data.len());
    let game = Game {
        players,
        child_offsets,
        children,
        info_ids,
        payoffs,
        action_offsets,
        chance,
        deals,
    };
    let start = Instant::now();
    for _ in 0..iterations {
        for updating in 0..2 {
            let deal = state.choose(&game.chance);
            let _ = traverse(&game, &mut state, 0, deal, updating);
        }
        state.iterations += 1;
    }
    let elapsed = start.elapsed().as_secs_f64();
    let mut out = Vec::new();
    out.extend_from_slice(MAGIC_OUT);
    put_u64(&mut out, state.iterations);
    put_u64(&mut out, state.node_visits);
    put_u64(&mut out, elapsed.to_bits());
    put_u32(&mut out, state.mt_index as u32);
    for x in state.mt {
        put_u32(&mut out, x);
    }
    for x in state.regrets {
        put_f64(&mut out, x);
    }
    for x in state.sums {
        put_f64(&mut out, x);
    }
    out.extend_from_slice(&state.visited);
    fs::write(&args[2], out).expect("write output");
}
