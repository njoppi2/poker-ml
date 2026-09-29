// Scratch-only protocol-compatible optimization candidate.  This intentionally
// mirrors game_engine/training/cfr_variants_kernel without changing it.
use std::{env, fs};

const IN: &[u8; 8] = b"LDCFRT01";
const OUT: &[u8; 8] = b"LDCFRO01";
const MAX_ACTIONS: usize = 16;
struct R {
    d: Vec<u8>,
    p: usize,
}
impl R {
    fn take(&mut self, n: usize) -> &[u8] {
        let a = self.p;
        self.p += n;
        &self.d[a..self.p]
    }
    fn u8(&mut self) -> u8 {
        self.take(1)[0]
    }
    fn u32(&mut self) -> u32 {
        u32::from_le_bytes(self.take(4).try_into().unwrap())
    }
    fn u64(&mut self) -> u64 {
        u64::from_le_bytes(self.take(8).try_into().unwrap())
    }
    fn f64(&mut self) -> f64 {
        f64::from_le_bytes(self.take(8).try_into().unwrap())
    }
}
fn pu64(out: &mut Vec<u8>, x: u64) {
    out.extend(x.to_le_bytes())
}
fn pf64(out: &mut Vec<u8>, x: f64) {
    out.extend(x.to_le_bytes())
}
struct G {
    players: Vec<i8>,
    offs: Vec<usize>,
    kids: Vec<usize>,
    infos: Vec<usize>,
    pays: Vec<f64>,
    chance: Vec<f64>,
    aoffs: Vec<usize>,
    deals: usize,
}
struct S {
    regrets: Vec<f64>,
    sums: Vec<f64>,
    visited: Vec<u8>,
    it: u64,
    visits: u64,
    variant: u8,
}

fn fill_strategies(s: &S, g: &G, out: &mut [f64]) {
    for info in 0..g.aoffs.len() - 1 {
        let (a, b) = (g.aoffs[info], g.aoffs[info + 1]);
        let mut total = 0.0;
        for i in a..b {
            total += s.regrets[i].max(0.0);
        }
        if total > 0.0 {
            for i in a..b {
                out[i] = s.regrets[i].max(0.0) / total;
            }
        } else {
            let p = 1.0 / (b - a) as f64;
            for i in a..b {
                out[i] = p;
            }
        }
    }
}
fn walk(
    g: &G,
    s: &mut S,
    st: &[f64],
    deltas: &mut [f64],
    index: usize,
    deal: usize,
    up: usize,
    own: f64,
    opp: f64,
) -> f64 {
    s.visits += 1;
    let pl = g.players[index];
    if pl < 0 {
        let v = g.pays[index * g.deals + deal];
        return if up == 0 { v } else { -v };
    }
    let info = g.infos[index * g.deals + deal];
    s.visited[info] = 1;
    let base = g.aoffs[info];
    let count = g.aoffs[info + 1] - base;
    assert!(count <= MAX_ACTIONS);
    let begin = g.offs[index];
    if pl as usize == up {
        let average_weight = if s.variant == 1 {
            s.it as f64 + 1.0
        } else {
            1.0
        };
        for a in 0..count {
            s.sums[base + a] += average_weight * g.chance[deal] * own * st[base + a];
        }
        let mut values = [0.0; MAX_ACTIONS];
        for a in 0..count {
            values[a] = walk(
                g,
                s,
                st,
                deltas,
                g.kids[begin + a],
                deal,
                up,
                own * st[base + a],
                opp,
            );
        }
        let mut value = 0.0;
        for a in 0..count {
            value += st[base + a] * values[a];
        }
        let weight = g.chance[deal] * opp;
        for a in 0..count {
            deltas[base + a] += weight * (values[a] - value);
        }
        value
    } else {
        let mut value = 0.0;
        for a in 0..count {
            value += st[base + a]
                * walk(
                    g,
                    s,
                    st,
                    deltas,
                    g.kids[begin + a],
                    deal,
                    up,
                    own,
                    opp * st[base + a],
                );
        }
        value
    }
}
fn discount(s: &mut S) {
    if s.variant != 2 || s.it == 0 {
        return;
    };
    let t = s.it as f64;
    let pos = t.powf(1.5) / (t.powf(1.5) + 1.0);
    let avg = (t / (t + 1.0)).powi(2);
    for x in &mut s.regrets {
        *x *= if *x > 0.0 { pos } else { 0.5 };
    }
    for x in &mut s.sums {
        *x *= avg;
    }
}
fn main() {
    let a: Vec<String> = env::args().collect();
    if a.len() != 3 {
        panic!("usage: kernel input output")
    }
    let mut r = R {
        d: fs::read(&a[1]).unwrap(),
        p: 0,
    };
    assert_eq!(r.take(8), IN);
    let niter = r.u64() as usize;
    let nn = r.u64() as usize;
    let nd = r.u64() as usize;
    let ni = r.u64() as usize;
    let ne = r.u64() as usize;
    let na = r.u64() as usize;
    let mut s = S {
        it: r.u64(),
        visits: r.u64(),
        variant: r.u8(),
        regrets: Vec::new(),
        sums: Vec::new(),
        visited: Vec::new(),
    };
    let players = (0..nn).map(|_| r.u8() as i8).collect();
    let offs = (0..nn + 1).map(|_| r.u64() as usize).collect();
    let kids = (0..ne).map(|_| r.u32() as usize).collect();
    let infos = (0..nn * nd).map(|_| r.u32() as usize).collect();
    let pays = (0..nn * nd).map(|_| r.f64()).collect();
    let chance = (0..nd).map(|_| r.f64()).collect();
    let aoffs = (0..ni + 1).map(|_| r.u64() as usize).collect();
    s.regrets = (0..na).map(|_| r.f64()).collect();
    s.sums = (0..na).map(|_| r.f64()).collect();
    s.visited = (0..ni).map(|_| r.u8()).collect();
    assert_eq!(r.p, r.d.len());
    let g = G {
        players,
        offs,
        kids,
        infos,
        pays,
        chance,
        aoffs,
        deals: nd,
    };
    let mut strategies = vec![0.0; na];
    let mut deltas = vec![0.0; na];
    for _ in 0..niter {
        discount(&mut s);
        for up in 0..2 {
            fill_strategies(&s, &g, &mut strategies);
            deltas.fill(0.0);
            for deal in 0..nd {
                walk(&g, &mut s, &strategies, &mut deltas, 0, deal, up, 1.0, 1.0);
            }
            for i in 0..na {
                let x = s.regrets[i] + deltas[i];
                s.regrets[i] = if s.variant == 1 { x.max(0.0) } else { x };
            }
        }
        s.it += 1;
    }
    let mut out = Vec::new();
    out.extend(OUT);
    pu64(&mut out, s.it);
    pu64(&mut out, s.visits);
    for x in s.regrets {
        pf64(&mut out, x)
    }
    for x in s.sums {
        pf64(&mut out, x)
    }
    out.extend(s.visited);
    fs::write(&a[2], out).unwrap();
}
