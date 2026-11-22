# Project Plan – Fireboy and Watergirl Multi-Agent RL

**Team:** Boshra, Aya, Firas, Mohamed
**Course:** Reinforcement Learning, University of Haifa (Prof. Teddy Lazebnik)
**Status:** project idea approved (22.11.2026); playable Python game ready

> The week numbers assume about 7 weeks. Shift them to match the real deadline.

---

## 1. Goal

Two agents with different abilities (Pink and Dude) must cooperate to finish a
Fireboy-and-Watergirl-style level. We compare three multi-agent RL approaches
and analyse how well, and how fast, they learn to cooperate.

**Main research question:** how do independent learning (IPPO), a shared policy,
and centralised training (MAPPO) compare on a cooperative task with sparse
rewards and agents that have different abilities?

**Follow-up questions:**
- How much does reward shaping matter? (E3, must)
- How much harder is the physics version than a grid version of the same level? (E4, must)
- Do the agents generalise to levels they never trained on? (E5, nice to have)

**Scope:** the guideline says groups of 4 (the maximum) are expected to deliver a
"larger" project, so E1–E4 are all must-do.

### Real-world relevance (graded: "potential real-world applications" and "practical impact")

The game is a small, controlled model of a common real problem: **a team of agents
with different abilities must coordinate without a central controller, and one
agent's mistake ends the mission for everyone.** Examples for the report:

- **Warehouse and logistics robots:** robots with different capabilities (lifting,
  scanning, opening doors) that must clear the way for each other.
- **Search-and-rescue teams of robots or drones:** each tolerates different hazards
  (heat, water, gas), like Pink and Dude with their fire colours.
- **Autonomous vehicles and traffic:** one vehicle has to wait or hold a position so
  another can pass safely (like holding a button while the other passes a door).
- **Multi-robot manipulation:** one robot holds or presses something while another
  works.

Things the project shows that carry over: how much centralised training helps,
how important reward design is when the real goal is rare, and how agents divide
roles. The report will also state the limits honestly: a 2D game is far simpler
than real robots (perfect observations, deterministic physics, no sensor noise).

### What is new in this project

- **True two-agent RL** on a Fireboy-and-Watergirl-style game with real platformer
  physics. The closest existing work (AyushG225/FireboyWatergirlRL) controls both
  characters with one policy and relies on imitation learning.
- **A systematic comparison** of three ways to organise multi-agent learning
  (independent, shared, centralised critic) on the same cooperative task.
- **A combination of techniques** to make sparse-reward cooperation learnable:
  potential-based reward shaping, a curriculum of easier level variants, and frame
  skip; each one measured with an ablation.
- **Same level, two difficulty settings** (physics vs grid), to measure how much the
  continuous dynamics make learning harder.
- An **environment with a verified game engine**: the physics was checked tick by
  tick against the original Java game.

---

## 2. What we have

- `fbwg/` – a Python port of the Java game
  [dylanroman03/FireAndWater-Game](https://github.com/dylanroman03/FireAndWater-Game):
  2 levels, original graphics, sounds and physics. The physics was checked to
  match the Java game exactly.
- Both heroes play at the same time. Keys: Pink W/A/D, Dude arrow keys.
- `fbwg/world.py` runs without a window at about 10,000–30,000 game ticks per
  second, and is deterministic (the same inputs always give the same result).

---

## 3. Formal definition (draft for the report)

A fully cooperative two-agent Markov game **M = ⟨N, S, {Aᵢ}, T, R, γ⟩**.

| Part | Definition |
|---|---|
| Agents | N = {Pink, Dude} |
| State S | Both heroes' positions, velocities, alive / at-door flags; positions of platforms and boxes; lever and button states; which gems are left; time step |
| Actions Aᵢ | 6 per agent: stay, left, right, jump, jump-left, jump-right. Each action is held for 8 game ticks (frame skip), giving 25 decisions per second |
| Transition T | The game physics (deterministic): gravity, collisions, levers/buttons moving platforms, pushable boxes |
| Terminal | A hero touches a deadly fire (Pink: blue/green, Dude: purple/green), both heroes reach their own doors, or the time limit is reached (for example 60 s = 1,500 decisions) |
| Reward R | Shared team reward, see below |
| Objective | Maximise E[Σ γᵗ rₜ], γ = 0.99 |

**Reward (starting values, to be tuned):**

| Event | Reward |
|---|---|
| Both heroes at their doors (win) | +10 |
| A hero reaches its own door | +2 (once) |
| A hero dies | −10 |
| Gem collected | +0.5 |
| First time a lever or button is used | +1 |
| Progress shaping: closer to own door (path distance on the tile grid) | + small, potential-based |
| Every decision | −0.001 |

**Observation per agent (vector, no images):** own position and velocity, the
other hero's position and velocity, both door positions, a small grid of tile
types around the agent (for example 7×7), platform / box positions, lever and
button states, an agent-ID flag.

---

## 4. Methods

| Method | Idea |
|---|---|
| **IPPO** (baseline) | Each agent has its own PPO network and treats the other as part of the environment |
| **Shared PPO** | One network controls both agents; the agent-ID flag tells it which hero it is |
| **MAPPO** | Separate actors, but during training a centralised critic sees the full state |

### Why these algorithms (graded: "justify ... based on the problem and state-of-the-art research")

| Property of our problem | Consequence for the algorithm |
|---|---|
| Discrete actions (6 per agent), vector observations | Policy-gradient methods (PPO) and value-based methods (DQN) both apply; PPO handles multiple agents and on-policy training more stably |
| Fully cooperative, one shared team reward | Multi-agent methods for cooperation: centralised training with decentralised execution (CTDE) is the standard approach |
| Two agents with **different** abilities | Test both separate networks (IPPO) and a shared network with an agent ID: does sharing help or hurt when roles differ? |
| Each agent's world changes as the other learns (non-stationarity) | MAPPO's centralised critic sees the full state, which is designed to reduce this problem |
| Sparse reward (win only at the end) | Reward shaping (potential-based, Ng et al. 1999, does not change the optimal policy) and a curriculum |

Support from research for the report:
- **PPO** (Schulman et al., 2017) is a stable, widely used policy-gradient method.
- **MAPPO** (Yu et al., 2022) showed that PPO with a centralised critic is a strong
  baseline on cooperative benchmarks (SMAC, Hanabi, MPE), often matching or beating
  off-policy methods such as QMIX.
- **IPPO** (de Witt et al., 2020) showed that independent PPO is a surprisingly
  strong baseline, so it is the fair starting point.
- **Value-decomposition methods** such as QMIX (Rashid et al., 2018) are an
  alternative; we discuss them as related work and add one only if time allows.

### Implementation

- Environment API: **PettingZoo ParallelEnv**
- Implementation: PyTorch, based on CleanRL's PPO (credit it in the report)
- Every experiment: **5 random seeds**, results shown as mean ± std

**Metrics:** success rate, mean episode return, episode length (time to solve),
death rate per hero, gems collected, sample efficiency (steps to reach 50% / 90% success).

**Qualitative analysis (behaviour of the trained agents):**
- Who presses which button or lever: do fixed roles appear (one helper, one runner)?
- Where and how the agents die (heatmaps of positions and death locations)
- Does one agent wait for the other?
- Videos of good and bad episodes for each method

---

## 5. Experiments

| # | Experiment | Priority |
|---|---|---|
| E1 | IPPO vs Shared PPO vs MAPPO on level 1 | **Must** |
| E2 | Hyperparameter tuning, see below | **Must** (required by the guideline) |
| E3 | Reward shaping and curriculum ablation: sparse reward vs shaped reward, with vs without curriculum | **Must** |
| E4 | Physics version vs a simple grid version of level 1 (also the backup plan, see §8) | **Must** |
| E5 | Extra generated levels: train on some, test on unseen ones (generator ideas adapted from AyushG225/FireboyWatergirlRL, with credit) | Nice to have |

### Hyperparameter search (E2)

1. **Short runs first:** about 20% of the full training budget, 2 seeds each.
2. **Random search, about 20 settings per method**, over:

   | Parameter | Range |
   |---|---|
   | Learning rate | 1e-4 to 1e-3 (log scale) |
   | Entropy coefficient | 0.001 to 0.05 (log scale) |
   | Rollout length (steps per update) | 512, 1024, 2048, 4096 |
   | PPO clip range | 0.1, 0.2, 0.3 |
   | Minibatches / epochs | 4–8 / 4–10 |
   | Network size | 2 layers of 64, 128 or 256 units |
   | Discount γ | 0.98, 0.99, 0.995 |
   | Frame skip | 4, 8, 12 game ticks |

3. **Best 3 settings per method:** full runs with 5 seeds.
4. **Report:** the search ranges, the chosen values, and a sensitivity plot for the
   2–3 most important parameters (learning rate, entropy).
5. **Same budget for every method** (same number of settings and environment
   steps), so the comparison in E1 is fair.

Tools: a small script of our own, or Optuna. Log everything with TensorBoard or Weights & Biases.

---

## 6. Timeline

| Week | Goal | Done when |
|---|---|---|
| 1 | Everyone runs the game; read the code; build the RL environment (PettingZoo) with actions, observations, rewards | A random agent runs 1,000 episodes with no errors |
| 2 | First training: IPPO on a simplified level 1 (for example fires removed) | The learning curve goes up |
| 3 | Full level 1; curriculum from easy to full; Shared PPO | At least one method sometimes solves level 1 |
| 4 | MAPPO; all 3 methods with 5 seeds (E1) | E1 results and plots |
| 5 | Hyperparameter search (E2); reward shaping and curriculum ablation (E3) | E2 and E3 results |
| 6 | Grid version and physics vs grid comparison (E4); behaviour analysis and videos; start the report | E4 results, draft report |
| 7 | Finish the report and presentation; clean the code; make results reproducible; E5 only if there is time | Submitted |

**Checkpoint at the end of week 3:** if no method solves even a simplified
level 1, switch the main experiments to the grid version (see §8).

---

## 7. Who does what (suggestion)

| Person | Main responsibility | Also |
|---|---|---|
| **Boshra** | RL environment: PettingZoo wrapper, observations, actions | Unit tests for the environment |
| **Aya** | Rewards and curriculum (easier level variants), extra levels | Repository management, README |
| **Firas** | Algorithms: IPPO and Shared PPO | Logging (TensorBoard), plots |
| **Mohamed** | Algorithms: MAPPO | Experiment runs (seeds, tuning), videos |
| **Everyone** | Report sections for their own part; presentation | Review each other's pull requests |

---

## 8. Risks and backup plans

| Risk | What we do |
|---|---|
| Agents don't learn with the physics (sparse reward, jump timing) | Reward shaping, curriculum, frame skip; if still failing by the week 3 checkpoint → grid version of the same level (one tile per step) |
| Training is too slow | Run the game headless, run several environments in parallel, use small networks, run overnight / on Colab |
| Unstable multi-agent training | More seeds, a smaller learning rate, MAPPO's central critic |
| The agents memorise one route | Random start positions; test on held-out levels (E5) |
| Merge conflicts | Git rules below |

---

## 9. Deliverables (from the course guideline)

- **Report:** 8–20 pages (not counting references), Arial 12, 1.5 line spacing, 1-inch margins.
  Sections: overview, problem formulation, methodology, results, discussion (including
  comparison to existing work and limitations), conclusion.
- **Code:** clean and commented, in Git, with clear instructions to reproduce the results.
  For reproducibility:
  - fixed random seeds for training and evaluation, recorded with every result
  - every experiment run from a saved config file (`experiments/configs/*.yaml`)
  - pinned package versions in `requirements.txt`
  - one command per figure or table in the report (for example `python experiments/run.py --config e1_mappo.yaml`)
  - trained models attached to a GitHub release, not committed to the repo
- **Presentation:** 15 minutes, with slides and a demo (video of the trained agents).
- **Grade:** final project 90%, presentation 10%.

---

## 10. Git rules

1. **Never push directly to `main`.** Each task gets its own branch:
   `git checkout -b feature/env-wrapper`
2. Commit small and often, with clear messages.
3. When done: push the branch, open a **Pull Request**, and one teammate reviews it before merging.
4. Before starting work: `git pull origin main`
5. Don't commit trained models, logs or `.venv` (already in `.gitignore`).

---

## 11. Related work and credits (for the report)

- **dylanroman03/FireAndWater-Game** (MIT): the original Java game. Our game is a Python port of it.
- **AyushG225/FireboyWatergirlRL** (MIT): an RL project on a similar game that controls
  **both characters with one policy** and needed imitation learning; plain PPO solved 0% of
  its levels. **Our difference:** true multi-agent RL with two separate agents.
- MAPPO: Yu et al., *The Surprising Effectiveness of PPO in Cooperative Multi-Agent Games* (2022).
- PPO: Schulman et al., *Proximal Policy Optimization Algorithms* (2017).
- IPPO: de Witt et al., *Is Independent Learning All You Need in the StarCraft Multi-Agent Challenge?* (2020).
- QMIX: Rashid et al., *QMIX: Monotonic Value Function Factorisation for Deep Multi-Agent RL* (2018).
- Reward shaping: Ng, Harada & Russell, *Policy Invariance Under Reward Transformations* (1999).
- Curriculum learning: Bengio et al., *Curriculum Learning* (2009).
- Sutton & Barto, *Reinforcement Learning: An Introduction* (course book).

---

## 12. Next steps (this week)

- [ ] Everyone: clone the repo and run `python play.py`
- [ ] Everyone: play level 1 together and write down how it is solved (this helps with rewards)
- [ ] Boshra: start the PettingZoo environment
- [ ] Aya: an easy version of level 1 (for example `levels/01_easy.txt` without fires)
- [ ] Firas + Mohamed: set up a PPO training script and test it on a simple Gymnasium task (for example CartPole)
- [ ] Aya: send the lecturer one line saying we switched from a grid to the physics version of the same idea
