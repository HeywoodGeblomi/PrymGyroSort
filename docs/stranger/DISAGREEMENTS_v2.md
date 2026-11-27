# Gamma-XCC rerun at c76dee0

Kernel commit c76dee0152a61f3ed2299fdec591e9ebab536777.
Housing numbers use the rebuilt 10,000-row public slice, with capped income 15.0001 and value 500001 kept. They do not use the 40-row sample in the repo.
The uncapped set drops every row at either of those caps from that same 10,000-row slice.
Diabetes is eight columns. PrymGyroSort ranks two columns only, so the diabetes front is the brute-force weak-dominance front.

## book

n=250. Brute front 7. Prym front 7. Fronts equal: True. Layer mismatches: 0. Locks: 15890.
Prym identity 968b5b2b85e9c402664f05a44b240ae657b70a57d56ef59e392cd567b12e0121.
pi_feas equals pi_raw: True. pi_empty equals pi_raw: False.

| Ranking | Off-front above a front row | Pairs | Front in top-|F| | Jaccard | Flips | Lock violations | Kendall vs Borda | Positions differ |
|---|---:|---:|---:|---|---:|---:|---:|---:|
| pi_raw | 163 | 182 | 3/7 | 3/11 | 4589 (4589/29786) | 0 | 2410 | 233 |
| pi_feas | 163 | 182 | 3/7 | 3/11 | 4589 (4589/29786) | 0 | 2410 | 233 |
| pi_empty | 163 | 182 | 3/7 | 3/11 | 4601 (4601/29786) | 0 | 2420 | 234 |
| borda | 98 | 115 | 3/7 | 3/11 | 2709 (2709/29786) | 0 | 0 | 0 |

Front rows outside the top |F| in pi_raw, worst first:
- B0056 position 170 gamma 25 borda 224 values [0.907044, 0.002251]
- B0227 position 12 gamma 196 borda 54 values [0.005062, 0.160808]
- B0113 position 11 gamma 197 borda 52 values [0.005062, 0.160808]
- B0170 position 10 gamma 204 borda 45 values [0.160808, 0.005062]
Unique axis winners on the front and outside the top |F|:
- B0056 axis 1 position 170 value 0.002251 gamma 25 borda 224

## diabetes

n=442. Brute front 75. Prym front None. Fronts equal: None. Layer mismatches: None. Locks: 17808.
pi_feas equals pi_raw: True. pi_empty equals pi_raw: True.

| Ranking | Off-front above a front row | Pairs | Front in top-|F| | Jaccard | Flips | Lock violations | Kendall vs Borda | Positions differ |
|---|---:|---:|---:|---|---:|---:|---:|---:|
| pi_raw | 273 | 1489 | 56/75 | 28/47 | 6374 (6374/79063) | 0 | 3363 | 417 |
| pi_feas | 273 | 1489 | 56/75 | 28/47 | 6374 (6374/79063) | 0 | 3363 | 417 |
| pi_empty | 273 | 1489 | 56/75 | 28/47 | 6374 (6374/79063) | 0 | 3363 | 417 |
| borda | 193 | 1448 | 55/75 | 11/19 | 4810 (4810/79063) | 0 | 0 | 0 |

Front rows outside the top |F| in pi_raw, worst first:
- D0405 position 348 gamma 72 borda 2035 values [0.12313149472988882, 0.08384370307932341, -0.10476542418529532, -0.10089508827529081, -0.0691723102806335, -0.002592261998183278, 0.03664373256235367, -0.03007244590430716]
- D0076 position 200 gamma 202 borda 1553 values [0.028284032228378497, 0.07007229917592636, -0.12678066991651324, -0.10684490904929198, -0.05444575906428573, -0.047980640675552584, -0.030747917533098208, 0.015490730158871856]
- D0246 position 178 gamma 233 borda 1594 values [-0.0320734439089463, -0.06189217872837582, 0.07961225881365488, 0.05098191569263361, 0.05600337505832251, -0.009972486173365287, 0.04506654937395887, -0.05906719430814835]
- D0261 position 172 gamma 241 borda 1482 values [-0.041773752573873474, 0.10450080893441897, 0.03558176735121902, -0.02573945744580244, 0.17749742259319157, -0.0763945037500033, -0.012908683225401873, 0.015490730158871856]
- D0127 position 162 gamma 247 borda 1420 values [-0.0018947058402839008, -0.012556124244455912, 0.03833367306762126, 0.013717248739678958, 0.07809320188284416, -0.03949338287409329, 0.004547695772676124, -0.09634615654165846]
- D0441 position 155 gamma 256 borda 1401 values [-0.07303030271641665, -0.08141314376144114, 0.08374011738825825, 0.027808929520208008, 0.17381578478910462, -0.03949338287409329, -0.00422151393810765, 0.0030644094143684884]
- D0281 position 150 gamma 261 borda 1298 values [-0.09027529589850945, -0.057313186930496314, -0.0249601584096303, -0.030436684372645465, -0.006584467611155497, -0.002592261998183278, 0.024055085357995654, 0.0030644094143684884]
- D0433 position 110 gamma 292 borda 1273 values [-0.06009655782984706, -0.029770379123702218, 0.04658939021682799, 0.019980217975469634, 0.12227285553188745, -0.03949338287409329, -0.05140387304727299, -0.009361911330134878]
- D0070 position 99 gamma 309 borda 1136 values [-0.06979686649477428, -0.012556124244455912, -0.00019300696201012598, -0.009142588970957101, 0.07072992627467027, -0.03949338287409329, -0.06291687914365544, 0.040343371647878594]
- D0387 position 97 gamma 314 borda 1147 values [0.015350287341808908, -0.07452744180974262, -0.04972730985725048, -0.017284448977484993, -0.028674294435677143, -0.002592261998183278, -0.10436552421115437, -0.07563562196748617]
- D0237 position 96 gamma 314 borda 1040 values [-0.06871905442089347, -0.06877788068007434, -0.00019300696201012598, -0.0010007289644291908, 0.04495846164606168, -0.03764832683029779, -0.04835926177554553, -0.0010776975004659671]
- D0269 position 95 gamma 316 borda 1144 values [-0.0320734439089463, -0.02632752814785296, 0.04246153164222462, -0.010395182818115238, 0.15908923357275687, -0.0763945037500033, -0.011896851335695978, -0.03835665973397607]
- 7 more
Unique axis winners on the front and outside the top |F|:
- D0281 axis 0 position 150 value -0.09027529589850945 gamma 261 borda 1298
- D0076 axis 2 position 200 value -0.12678066991651324 gamma 202 borda 1553

## housing_10k_capped

n=10000. Brute front 31. Prym front 31. Fronts equal: True. Layer mismatches: 0. Locks: 37265479.
Prym identity 22cc811f06d78cf00792d4ccf941e96a09cd62b26170d9e58a93bcbc722fa67a.
pi_feas equals pi_raw: True. pi_empty equals pi_raw: False.

| Ranking | Off-front above a front row | Pairs | Front in top-|F| | Jaccard | Flips | Lock violations | Kendall vs Borda | Positions differ |
|---|---:|---:|---:|---|---:|---:|---:|---:|
| pi_raw | 0 | 0 | 31/31 | 1/1 | 3882169 (3882169/49827939) | 0 | 2353821 | 9985 |
| pi_feas | 0 | 0 | 31/31 | 1/1 | 3882169 (3882169/49827939) | 0 | 2353821 | 9985 |
| pi_empty | 155 | 2403 | 7/31 | 7/55 | 3888024 (3888024/49827939) | 10105 | 2347579 | 9960 |
| borda | 127 | 2079 | 7/31 | 7/55 | 2527695 (2527695/49827939) | 10573 | 0 | 0 |

No front row is outside the top |F|. Worst front position: H08878 at 31 gamma 9969 borda 439 values [15.0001, 500001.0].

## housing_uncapped

n=9516. Brute front 6. Prym front 6. Fronts equal: True. Layer mismatches: 0. Locks: 33001716.
Prym identity ab00f1847841b25355ef14852101a5b9f5bd6923efccdb5c831d84fea9da9108.
pi_feas equals pi_raw: True. pi_empty equals pi_raw: False.

| Ranking | Off-front above a front row | Pairs | Front in top-|F| | Jaccard | Flips | Lock violations | Kendall vs Borda | Positions differ |
|---|---:|---:|---:|---|---:|---:|---:|---:|
| pi_raw | 66 | 116 | 4/6 | 1/2 | 4342297 (4342297/45101320) | 0 | 2236954 | 9469 |
| pi_feas | 66 | 116 | 4/6 | 1/2 | 4342297 (4342297/45101320) | 0 | 2236954 | 9469 |
| pi_empty | 71 | 121 | 4/6 | 1/2 | 4342466 (4342466/45101320) | 68 | 2237100 | 9471 |
| borda | 63 | 108 | 4/6 | 1/2 | 2181528 (2181528/45101320) | 31 | 0 | 0 |

Front rows outside the top |F| in pi_raw, worst first:
- H09810 position 72 gamma 9203 borda 320 values [6.777, 500000.0]
- H01564 position 53 gamma 9263 borda 252 values [12.5915, 432400.0]
Unique axis winners on the front and outside the top |F|:
- H01564 axis 0 position 53 value 12.5915 gamma 9263 borda 252

## abalone

n=4177. Brute front 5. Prym front 5. Fronts equal: True. Layer mismatches: 0. Locks: 8197314.
Prym identity 052efa5efb70e8c533aaa4ef09d8eb3fe7ae80ec027f28e38ce300d94831f7e7.
pi_feas equals pi_raw: True. pi_empty equals pi_raw: False.

| Ranking | Off-front above a front row | Pairs | Front in top-|F| | Jaccard | Flips | Lock violations | Kendall vs Borda | Positions differ |
|---|---:|---:|---:|---|---:|---:|---:|---:|
| pi_raw | 20 | 26 | 3/5 | 3/7 | 227251 (227251/8709322) | 0 | 115700 | 4097 |
| pi_feas | 20 | 26 | 3/5 | 3/7 | 227251 (227251/8709322) | 0 | 115700 | 4097 |
| pi_empty | 18 | 24 | 3/5 | 3/7 | 237991 (237991/8709322) | 4577 | 112554 | 4104 |
| borda | 12 | 15 | 3/5 | 3/7 | 156549 (156549/8709322) | 2593 | 0 | 0 |

Front rows outside the top |F| in pi_raw, worst first:
- A0891 position 25 gamma 4129 borda 47 values [0.73, 2.8255]
- A1428 position 10 gamma 4154 borda 22 values [0.815, 2.255]
Unique axis winners on the front and outside the top |F|:
- A1428 axis 0 position 10 value 0.815 gamma 4154 borda 22
- A0891 axis 1 position 25 value 2.8255 gamma 4129 borda 47

## Deltas against the pre-fix artifact hashes

Book seal d6f5cf4f, output 4b06895a. Layers and the Gamma order are unchanged: front 7, 163 off-front rows, 182 pairs, Jaccard 3/11, 4589 flips, 0 lock violations in pi_raw and pi_feas, 15890 locks. Borda was not in that run.
Diabetes seal fcf25f52, output 0b3de96f. Eight-column brute layers, not the 2-D kernel. Prior: front 75, Kendall 3363, 417 positions differ, 273 off-front rows, 1489 pairs, Jaccard 28/47, 6374 flips, 0 lock violations, buried D0076 at 200 and D0281 at 150.
Housing 10k seal 99cd76c0, output 8891d1b2. Prym then reported front 32, identity 3a94ab31, with H01566 extra (an extra pre-fix tie-bug row, at 650), 37265479 locks, pi_raw Kendall 2353821, 9985 positions differ, 618 off-front rows, Jaccard 31/33, 3984588 flips, 0 pi_raw lock violations.
Uncapped housing seal 8f0b150d, output 183c214b. Metrics were already on the brute-force layers: front 6, 4 of 6 in the top, Jaccard 1/2, Kendall 2236954, 9469 positions differ, 0 pi_raw lock violations, H09810 at 72 and H01564 at 53. Prym identity then was 4a7d328e because the kernel layers differed.
Abalone seal 09a5e4e5, output d8a518ba. Metrics were on the 5-row brute front: 3 of 5 in the top, Jaccard 3/7, Kendall 115700, 4097 positions differ, 0 pi_raw lock violations, A1428 at 10 and A0891 at 25. Prym then reported front 6, identity d88ece5b, with A3715 extra.
