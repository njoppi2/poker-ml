use std::{env, fs, time::Instant};
const IN: &[u8; 8] = b"LDADV002";
const OUT: &[u8; 8] = b"LDADVOUT";
struct R {
    d: Vec<u8>,
    p: usize,
}
impl R {
    fn b(&mut self, n: usize) -> Vec<u8> {
        let x = self.d[self.p..self.p + n].to_vec();
        self.p += n;
        x
    }
    fn u64(&mut self) -> usize {
        usize::try_from(u64::from_le_bytes(self.b(8).try_into().unwrap())).unwrap()
    }
    fn f64(&mut self) -> f64 {
        f64::from_le_bytes(self.b(8).try_into().unwrap())
    }
    fn f64s(&mut self, n: usize) -> Vec<f64> {
        (0..n).map(|_| self.f64()).collect()
    }
    fn u32s(&mut self, n: usize) -> Vec<usize> {
        (0..n)
            .map(|_| u32::from_le_bytes(self.b(4).try_into().unwrap()) as usize)
            .collect()
    }
    fn u64s(&mut self, n: usize) -> Vec<usize> {
        (0..n).map(|_| self.u64()).collect()
    }
}
fn u(o: &mut Vec<u8>, x: usize) {
    o.extend_from_slice(&(x as u64).to_le_bytes())
}
fn f(o: &mut Vec<u8>, x: f64) {
    o.extend_from_slice(&x.to_le_bytes())
}
struct G {
    pl: Vec<i8>,
    ip: Vec<i8>,
    co: Vec<usize>,
    ch: Vec<usize>,
    inf: Vec<usize>,
    pay: Vec<f64>,
    ao: Vec<usize>,
    chance: Vec<f64>,
    n: usize,
    d: usize,
    ni: usize,
    na: usize,
}
impl G {
    fn range(&self, i: usize) -> std::ops::Range<usize> {
        self.ao[i]..self.ao[i + 1]
    }
    fn at(&self, node: usize, deal: usize) -> usize {
        node * self.d + deal
    }
}
fn simplex(row: &mut [f64]) {
    let mut s = row.to_vec();
    s.sort_by(|a, b| b.total_cmp(a));
    let mut sum = 0.;
    let mut rho = 0;
    for (j, &v) in s.iter().enumerate() {
        sum += v;
        if v - (sum - 1.) / (j + 1) as f64 > 0. {
            rho = j + 1
        }
    }
    let th = (s[..rho].iter().sum::<f64>() - 1.) / rho as f64;
    for x in row {
        *x = (*x - th).max(0.)
    }
}
fn joint(g: &G, a: &[f64], b: &[f64]) -> Vec<f64> {
    let mut r = vec![0.; g.na];
    for i in 0..g.ni {
        let src = if g.ip[i] == 0 { a } else { b };
        r[g.range(i)].copy_from_slice(&src[g.range(i)])
    }
    r
}
fn br(g: &G, p: &[f64], who: usize) -> (f64, Vec<f64>) {
    let mut reach = vec![0.; g.n * g.d];
    reach[..g.d].copy_from_slice(&g.chance);
    for n in 0..g.n {
        if g.pl[n] < 0 {
            continue;
        }
        for a in 0..g.co[n + 1] - g.co[n] {
            let c = g.ch[g.co[n] + a];
            for deal in 0..g.d {
                let x = reach[g.at(n, deal)];
                let info = g.inf[g.at(n, deal)];
                reach[g.at(c, deal)] = if g.pl[n] as usize == who {
                    x
                } else {
                    x * p[g.ao[info] + a]
                }
            }
        }
    }
    let mut val = vec![0.; g.n * g.d];
    let mut chosen = vec![0usize; g.ni];
    let mut score = vec![0.; g.na];
    for n in (0..g.n).rev() {
        if g.pl[n] < 0 {
            for d in 0..g.d {
                val[g.at(n, d)] = g.pay[g.at(n, d)] * if who == 0 { 1. } else { -1. };
            }
        } else if g.pl[n] as usize == who {
            for d in 0..g.d {
                let info = g.inf[g.at(n, d)];
                for value in &mut score[g.range(info)] {
                    *value = 0.;
                }
            }
            for a in 0..g.co[n + 1] - g.co[n] {
                let c = g.ch[g.co[n] + a];
                for d in 0..g.d {
                    let info = g.inf[g.at(n, d)];
                    score[g.ao[info] + a] += reach[g.at(n, d)] * val[g.at(c, d)]
                }
            }
            for d in 0..g.d {
                let info = g.inf[g.at(n, d)];
                let r = g.range(info);
                let mut best = 0;
                for a in 1..r.len() {
                    if score[r.start + a] > score[r.start + best] {
                        best = a
                    }
                }
                chosen[info] = best;
                val[g.at(n, d)] = val[g.at(g.ch[g.co[n] + best], d)]
            }
        } else {
            for d in 0..g.d {
                let info = g.inf[g.at(n, d)];
                let mut x = 0.;
                for a in 0..g.co[n + 1] - g.co[n] {
                    x += p[g.ao[info] + a] * val[g.at(g.ch[g.co[n] + a], d)]
                }
                val[g.at(n, d)] = x
            }
        }
    }
    let mut out = p.to_vec();
    for i in 0..g.ni {
        if g.ip[i] as usize == who {
            for x in &mut out[g.range(i)] {
                *x = 0.
            }
            out[g.ao[i] + chosen[i]] = 1.
        }
    }
    (
        g.chance.iter().enumerate().map(|(d, x)| x * val[d]).sum(),
        out,
    )
}
fn cf(g: &G, p: &[f64], who: usize) -> Vec<f64> {
    let mut reach = vec![0.; g.n * g.d];
    reach[..g.d].copy_from_slice(&g.chance);
    for n in 0..g.n {
        if g.pl[n] < 0 {
            continue;
        }
        for a in 0..g.co[n + 1] - g.co[n] {
            let c = g.ch[g.co[n] + a];
            for d in 0..g.d {
                let x = reach[g.at(n, d)];
                let info = g.inf[g.at(n, d)];
                reach[g.at(c, d)] = if g.pl[n] as usize == who {
                    x
                } else {
                    x * p[g.ao[info] + a]
                }
            }
        }
    }
    let mut val = vec![0.; g.n * g.d];
    let mut q = vec![0.; g.na];
    for n in (0..g.n).rev() {
        if g.pl[n] < 0 {
            for d in 0..g.d {
                val[g.at(n, d)] = g.pay[g.at(n, d)] * if who == 0 { 1. } else { -1. }
            }
        } else {
            for d in 0..g.d {
                let info = g.inf[g.at(n, d)];
                let mut x = 0.;
                for a in 0..g.co[n + 1] - g.co[n] {
                    x += p[g.ao[info] + a] * val[g.at(g.ch[g.co[n] + a], d)]
                }
                val[g.at(n, d)] = x
            }
            if g.pl[n] as usize == who {
                for a in 0..g.co[n + 1] - g.co[n] {
                    let c = g.ch[g.co[n] + a];
                    for d in 0..g.d {
                        let info = g.inf[g.at(n, d)];
                        q[g.ao[info] + a] += reach[g.at(n, d)] * val[g.at(c, d)]
                    }
                }
            }
        }
    }
    q
}
fn update(g: &G, p: &mut [f64], q0: &[f64], q1: &[f64], alpha: f64) {
    for i in 0..g.ni {
        let q = if g.ip[i] == 0 { q0 } else { q1 };
        let r = g.range(i);
        for a in r.clone() {
            p[a] += alpha * q[a]
        }
        simplex(&mut p[r])
    }
}
fn regret_policy(g: &G, regrets: &[f64]) -> Vec<f64> {
    let mut p = vec![0.; g.na];
    for i in 0..g.ni {
        let r = g.range(i);
        let total: f64 = regrets[r.clone()].iter().map(|x| x.max(0.)).sum();
        if total > 0. {
            for a in r.clone() {
                p[a] = regrets[a].max(0.) / total;
            }
        } else {
            for a in r.clone() {
                p[a] = 1. / r.len() as f64;
            }
        }
    }
    p
}
fn own_weights(g: &G, p: &[f64], who: usize) -> Vec<f64> {
    let mut reach = vec![0.; g.n * g.d];
    reach[..g.d].copy_from_slice(&g.chance);
    let mut weights = vec![0.; g.ni];
    for n in 0..g.n {
        if g.pl[n] < 0 {
            continue;
        }
        if g.pl[n] as usize == who {
            for d in 0..g.d {
                weights[g.inf[g.at(n, d)]] += reach[g.at(n, d)];
            }
        }
        for a in 0..g.co[n + 1] - g.co[n] {
            let c = g.ch[g.co[n] + a];
            for d in 0..g.d {
                let info = g.inf[g.at(n, d)];
                reach[g.at(c, d)] = if g.pl[n] as usize == who {
                    reach[g.at(n, d)] * p[g.ao[info] + a]
                } else {
                    reach[g.at(n, d)]
                };
            }
        }
    }
    weights
}
fn main() {
    let a: Vec<String> = env::args().collect();
    if a.len() != 3 {
        panic!("usage")
    };
    let mut r = R {
        d: fs::read(&a[1]).unwrap(),
        p: 0,
    };
    assert_eq!(r.b(8).as_slice(), IN);
    let mode = r.u64();
    assert!(mode <= 5);
    let advance = r.u64();
    let n = r.u64();
    let d = r.u64();
    let ni = r.u64();
    let edges = r.u64();
    let na = r.u64();
    let mut iter = r.u64();
    let snaps = r.u64();
    let step = r.f64();
    let refresh = r.u64();
    let max = r.u64();
    let selfw = r.f64();
    let exploiter_step_multiplier = r.f64();
    assert!(
        step.is_finite()
            && step > 0.
            && refresh > 0
            && max > 0
            && selfw >= 0.
            && selfw <= 1.
            && exploiter_step_multiplier.is_finite()
            && exploiter_step_multiplier > 0.
    );
    let pl: Vec<i8> = (0..n).map(|_| r.b(1)[0] as i8).collect();
    let co = r.u64s(n + 1);
    let ch = r.u32s(edges);
    let inf = r.u32s(n * d);
    let pay = r.f64s(n * d);
    let chance = r.f64s(d);
    let ao = r.u64s(ni + 1);
    let mut ip = vec![-1; ni];
    for node in 0..n {
        if pl[node] < 0 {
            continue;
        }
        for &info in &inf[node * d..(node + 1) * d] {
            assert!(ip[info] < 0 || ip[info] == pl[node]);
            ip[info] = pl[node];
        }
    }
    assert!(ip.iter().all(|player| *player >= 0));
    let g = G {
        pl,
        ip,
        co,
        ch,
        inf,
        pay,
        ao,
        chance,
        n,
        d,
        ni,
        na,
    };
    let mut p = r.f64s(na);
    let mut regrets = if mode == 2 { r.f64s(na) } else { Vec::new() };
    let mut sums = if mode == 2 { r.f64s(na) } else { Vec::new() };
    let mut pool = Vec::new();
    for _ in 0..snaps {
        pool.push((r.f64s(na), r.f64s(na)))
    }
    assert_eq!(r.p, r.d.len());
    let start = Instant::now();
    for _ in 0..advance {
        if (mode == 1 || mode == 3 || mode == 4) && (pool.is_empty() || iter % refresh == 0) {
            let (_, a0) = br(&g, &p, 0);
            let (_, a1) = br(&g, &p, 1);
            pool.push((a0, a1));
            if pool.len() > max {
                pool.remove(0);
            }
        }
        let alpha = step / ((iter + 1) as f64).sqrt();
        if mode == 2 {
            p = regret_policy(&g, &regrets);
            let (_, b0) = br(&g, &p, 0);
            let (_, b1) = br(&g, &p, 1);
            let q0 = cf(&g, &joint(&g, &p, &b1), 0);
            let q1 = cf(&g, &joint(&g, &b0, &p), 1);
            for who in 0..2 {
                let q = if who == 0 { &q0 } else { &q1 };
                let weights = own_weights(&g, &p, who);
                for i in 0..g.ni {
                    if g.ip[i] as usize != who {
                        continue;
                    };
                    let r = g.range(i);
                    let v: f64 = r.clone().map(|a| p[a] * q[a]).sum();
                    for a in r {
                        regrets[a] += q[a] - v;
                        sums[a] += weights[i] * p[a];
                    }
                }
            }
        } else if mode == 0 {
            let (_, b0) = br(&g, &p, 0);
            let (_, b1) = br(&g, &p, 1);
            let q0 = cf(&g, &joint(&g, &p, &b1), 0);
            let q1 = cf(&g, &joint(&g, &b0, &p), 1);
            update(&g, &mut p, &q0, &q1, alpha)
        } else if mode == 5 {
            // Look ahead along a provisional ED path, but apply the average
            // response to the original policy in one simultaneous update.
            let mut probe = p.clone();
            let mut q0 = vec![0.; g.na];
            let mut q1 = vec![0.; g.na];
            let mut response_weight = 1.;
            let mut total_weight = 0.;
            for look in 0..max {
                let (_, b0) = br(&g, &probe, 0);
                let (_, b1) = br(&g, &probe, 1);
                let against0 = cf(&g, &joint(&g, &p, &b1), 0);
                let against1 = cf(&g, &joint(&g, &b0, &p), 1);
                for a in 0..g.na {
                    q0[a] += response_weight * against0[a];
                    q1[a] += response_weight * against1[a];
                }
                total_weight += response_weight;
                response_weight *= exploiter_step_multiplier;
                if look + 1 < max {
                    if look == 0 {
                        // Here probe and p are identical; reuse the scores.
                        update(&g, &mut probe, &against0, &against1, alpha);
                    } else {
                        let probe0 = cf(&g, &joint(&g, &probe, &b1), 0);
                        let probe1 = cf(&g, &joint(&g, &b0, &probe), 1);
                        update(&g, &mut probe, &probe0, &probe1, alpha);
                    }
                }
            }
            if selfw > 0. {
                let self0 = cf(&g, &p, 0);
                let self1 = cf(&g, &p, 1);
                for a in 0..g.na {
                    q0[a] = (1. - selfw) * q0[a] / total_weight + selfw * self0[a];
                    q1[a] = (1. - selfw) * q1[a] / total_weight + selfw * self1[a];
                }
            } else {
                for a in 0..g.na {
                    q0[a] /= total_weight;
                    q1[a] /= total_weight;
                }
            }
            update(&g, &mut p, &q0, &q1, alpha)
        } else if mode == 4 {
            // Both policies learn from the same pre-update state. The
            // exploiter pair contains one independent policy for each seat.
            let (q0_target, q1_target, q0_exploiter, q1_exploiter) = {
                let current = pool.last().unwrap();
                let q0_against = cf(&g, &joint(&g, &p, &current.1), 0);
                let q1_against = cf(&g, &joint(&g, &current.0, &p), 1);
                let q0_self = cf(&g, &p, 0);
                let q1_self = cf(&g, &p, 1);
                let q0_target: Vec<f64> = q0_against
                    .iter()
                    .zip(&q0_self)
                    .map(|(foe, own)| (1. - selfw) * foe + selfw * own)
                    .collect();
                let q1_target: Vec<f64> = q1_against
                    .iter()
                    .zip(&q1_self)
                    .map(|(foe, own)| (1. - selfw) * foe + selfw * own)
                    .collect();
                let q0_exploiter = cf(&g, &joint(&g, &current.0, &p), 0);
                let q1_exploiter = cf(&g, &joint(&g, &p, &current.1), 1);
                (q0_target, q1_target, q0_exploiter, q1_exploiter)
            };
            update(&g, &mut p, &q0_target, &q1_target, alpha);
            let current = pool.last_mut().unwrap();
            let adversary_alpha = alpha * exploiter_step_multiplier;
            for info in 0..g.ni {
                let range = g.range(info);
                let (adversary, scores) = if g.ip[info] == 0 {
                    (&mut current.0, &q0_exploiter)
                } else {
                    (&mut current.1, &q1_exploiter)
                };
                for action in range.clone() {
                    adversary[action] += adversary_alpha * scores[action];
                }
                simplex(&mut adversary[range]);
            }
        } else if mode == 3 {
            // Two complete opponents contribute to one projected update.
            // Mixing their separate counterfactual scores preserves the
            // match-level opponent mixture; mixing action rows would not.
            let current = pool.last().unwrap();
            let q0_exploiter = cf(&g, &joint(&g, &p, &current.1), 0);
            let q1_exploiter = cf(&g, &joint(&g, &current.0, &p), 1);
            let q0_self = cf(&g, &p, 0);
            let q1_self = cf(&g, &p, 1);
            let q0: Vec<f64> = q0_exploiter
                .iter()
                .zip(&q0_self)
                .map(|(opponent, own)| (1. - selfw) * opponent + selfw * own)
                .collect();
            let q1: Vec<f64> = q1_exploiter
                .iter()
                .zip(&q1_self)
                .map(|(opponent, own)| (1. - selfw) * opponent + selfw * own)
                .collect();
            update(&g, &mut p, &q0, &q1, alpha)
        } else {
            let before = (iter as f64 * selfw).floor() as usize;
            let use_self = ((iter as f64 + 1.) * selfw).floor() as usize > before;
            let pool_turn = iter - before;
            let opp1 = if use_self {
                &p
            } else {
                &pool[pool_turn % pool.len()].1
            };
            let opp0 = if use_self {
                &p
            } else {
                &pool[pool_turn % pool.len()].0
            };
            let q0 = cf(&g, &joint(&g, &p, opp1), 0);
            let q1 = cf(&g, &joint(&g, opp0, &p), 1);
            update(&g, &mut p, &q0, &q1, alpha)
        }
        iter += 1;
    }
    let mut o = Vec::new();
    o.extend_from_slice(OUT);
    u(&mut o, iter);
    u(&mut o, pool.len());
    f(&mut o, start.elapsed().as_secs_f64());
    for x in &p {
        f(&mut o, *x)
    }
    if mode == 2 {
        for x in regrets {
            f(&mut o, x)
        }
        for x in sums {
            f(&mut o, x)
        }
    }
    for (x, y) in pool {
        for z in x {
            f(&mut o, z)
        }
        for z in y {
            f(&mut o, z)
        }
    }
    fs::write(&a[2], o).unwrap();
}
