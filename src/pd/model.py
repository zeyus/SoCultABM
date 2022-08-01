###
# pyflamegpu Prisoner's Dilemma Agent Based Model
###

# Import pyflamegpu
import pyflamegpu
# Import standard python libs that are used
import sys, random, math

# Define some constants
RANDOM_SEED: int = 69420
MAX_AGENT_COUNT: int = 16384 # if you change this please change the value in interact.cu
INIT_AGENT_COUNT: int = MAX_AGENT_COUNT // 4
STEP_COUNT: int = 10000
VERBOSE_OUTPUT: bool = False
ENV_MAX: int = math.ceil(math.sqrt(MAX_AGENT_COUNT))
USE_VISUALISATION: bool = True
VISUALISE_COMMUNICATION_GRID = False

# Define the environment
INIT_COOP_FREQ: float = 0.5
COST_OF_LIVING: float = 0.5
PAYOFF_CD: float = -1.0
MAX_PLAY_DISTANCE: int = 1 # radius of message search grid

REPRODUCE_MIN_ENERGY: float = 100.0
REPRODUCE_COST: float = 50.0
PAYOFF_CC: float = 3.0
PAYOFF_DC: float = 5.0
MAX_ENERGY: float = 150.0
MAX_INIT_ENERGY: float = 50.0

CUDA_SRC_PATH: str = "src/pd/cudasrc"
CUDA_SEARCH_FUNC: str = "search"
CUDA_INTERACT_FUNC: str = "interact"

ROLL_RADS_270: float = 3 * math.pi / 2
AGENT_TRAVEL_STRATEGIES: list = ["random"]
AGENT_TRAVEL_STRATEGY: int = AGENT_TRAVEL_STRATEGIES.index("random")
AGENT_TRAVEL_COST = 0.0
AGENT_DEFAULT_SHAPE: str = './src/resources/models/primitive_pyramid.obj'
AGENT_DEFAULT_SCALE: float = 1 / 2.0
AGENT_STRATEGIES: list = {
  "always_coop": {
    "name": "always_coop",
    "id": 0,
    "proportion": 0.50,
  },
  "always_cheat": {
    "name": "always_cheat",
    "id": 1,
    "proportion": 0.25,
  },
  "tit_for_tat": {
    "name": "tit_for_tat",
    "id": 2,
    "proportion": 0.15,
  },
  "random": {
    "name": "random",
    "id": 3,
    "proportion": 0.10,
  },
}
AGENT_WEIGHTS = [AGENT_STRATEGIES[strategy]["proportion"] for strategy in AGENT_STRATEGIES]
AGENT_STRATEGY_IDS = [AGENT_STRATEGIES[strategy]["id"] for strategy in AGENT_STRATEGIES]
AGENT_TRAITS = [
  0,
  1,
  2,
  3
]

AGENT_STRATEGY_PER_TRAIT = False

AGENT_TRAIT_MUTATION_RATE = 0.05

# definie color pallete for each agent strategy, with fallback to white
AGENT_COLOR_SCHEME: pyflamegpu.uDiscreteColor = pyflamegpu.uDiscreteColor("agent_trait", pyflamegpu.SET1, pyflamegpu.WHITE)



# Define a method which when called will define the model, Create the simulation object and execute it.
def main():
  print(ENV_MAX)
  # Define the FLAME GPU model
  model: pyflamegpu.ModelDescription = pyflamegpu.ModelDescription("prisoners_dilemma")
  # Define the location message list
  message: pyflamegpu.MessageArray2D_Description = model.newMessageArray2D("player_search_msg")
  message.newVariableID("id")
  message.newVariableUInt("grid_index")
  # create array to fit all agents
  message.setDimensions(ENV_MAX, ENV_MAX)

  agent: pyflamegpu.AgentDescription = model.newAgent("prisoner")
  agent.newVariableID("id")
  agent.newVariableArrayUInt("agent_strategies")
  agent.newVariableUInt("agent_trait")
  agent.newVariableUInt("x_a")
  agent.newVariableUInt("y_a")
  agent.newVariableUInt("grid_index")
  agent.newVariableFloat("energy")
  if USE_VISUALISATION:
    agent.newVariableFloat("x")
    agent.newVariableFloat("y")
  # load agent-specific interactions
  agent_search_fn: pyflamegpu.AgentFunctionDescription = agent.newRTCFunctionFile(CUDA_SEARCH_FUNC, '.'.join(['/'.join([CUDA_SRC_PATH, CUDA_SEARCH_FUNC]), 'cu']))
  agent_search_fn.setMessageOutput("player_search_msg")
  agent_move_fn: pyflamegpu.AgentFunctionDescription = agent.newRTCFunctionFile(CUDA_INTERACT_FUNC, '.'.join(['/'.join([CUDA_SRC_PATH, CUDA_INTERACT_FUNC]), 'cu']))
  agent_move_fn.setMessageInput("player_search_msg")
  agent_move_fn.setAllowAgentDeath(True)
  
  # Environment properties
  env: pyflamegpu.EnvironmentDescription = model.Environment()
  env.newPropertyUInt("env_max", ENV_MAX)
  env.newPropertyUInt("max_agents", MAX_AGENT_COUNT)
  env.newPropertyFloat("max_energy", MAX_ENERGY)
  env.newPropertyUInt("max_play_distance", MAX_PLAY_DISTANCE)
  env.newPropertyFloat("init_coop_freq", INIT_COOP_FREQ)
  env.newPropertyFloat("cost_of_living", COST_OF_LIVING)
  env.newPropertyFloat("payoff_cd", PAYOFF_CD)
  env.newPropertyFloat("payoff_cc", PAYOFF_CC)
  env.newPropertyFloat("payoff_dc", PAYOFF_DC)
  env.newPropertyFloat("reproduce_min_energy", REPRODUCE_MIN_ENERGY)
  env.newPropertyFloat("reproduce_cost", REPRODUCE_COST)
  env.newPropertyFloat("travel_strategy", AGENT_TRAVEL_STRATEGY)
  env.newPropertyFloat("travel_cost", AGENT_TRAVEL_COST)

  # define playspace
  env.newMacroPropertyUInt("playspace", MAX_AGENT_COUNT, MAX_AGENT_COUNT)

  # Layer #1
  layer1: pyflamegpu.LayerDescription = model.newLayer()
  layer1.addAgentFunction("prisoner", CUDA_SEARCH_FUNC)
  # Layer #2
  layer2: pyflamegpu.LayerDescription = model.newLayer()
  layer2.addAgentFunction("prisoner", CUDA_INTERACT_FUNC)


  simulation: pyflamegpu.CUDASimulation = pyflamegpu.CUDASimulation(model)

  if pyflamegpu.VISUALISATION:
    visualisation: pyflamegpu.ModelVis  = simulation.getVisualisation()
    # Configure the visualiastion.
    INIT_CAM = ENV_MAX / 2.0
    visualisation.setInitialCameraLocation(INIT_CAM, INIT_CAM, ENV_MAX)
    visualisation.setInitialCameraTarget(INIT_CAM, INIT_CAM, 0.0)
    visualisation.setCameraSpeed(0.1)
    # do not limit speed
    visualisation.setSimulationSpeed(0)
    
    vis_agent: pyflamegpu.AgentVis = visualisation.addAgent("prisoner")

    # Set the model to use, and scale it.
    vis_agent.setModel(AGENT_DEFAULT_SHAPE)
    vis_agent.setModelScale(AGENT_DEFAULT_SCALE)
    vis_agent.setColor(AGENT_COLOR_SCHEME)
    
    # Activate the visualisation.
    visualisation.activate()

  # set some simulation defaults
  if RANDOM_SEED is not None:
    simulation.SimulationConfig().random_seed = RANDOM_SEED
  simulation.SimulationConfig().steps = STEP_COUNT
  simulation.SimulationConfig().verbose = VERBOSE_OUTPUT

   # Initialise the simulation
  simulation.initialise(sys.argv)

  # Generate a population if an initial states file is not provided
  if not simulation.SimulationConfig().input_file:
    # Seed the host RNG using the cuda simulations' RNG
    if RANDOM_SEED is not None:
      random.seed(simulation.SimulationConfig().random_seed)
    # Generate a vector of agents
    population = pyflamegpu.AgentVector(agent, INIT_AGENT_COUNT)
    # Iterate the population, initialising per-agent values
    instance: pyflamegpu.AgentVector_Agent
    # randomly create starting position for agents
    import numpy as np
    if RANDOM_SEED is not None:
      np.random.RandomState(RANDOM_SEED)
    # initialise grid with id for all possible agents
    grid = np.arange(MAX_AGENT_COUNT, dtype=np.uint32)
    # shuffle grid
    np.random.shuffle(grid)
    # reshape it to match the environment size
    grid = np.reshape(grid, (ENV_MAX, ENV_MAX))
    # initialise agents
    for i, instance in enumerate(population):
      # find agent position in grid
      pos = np.where(grid == i)
      x = pos[0][0].item()
      y = pos[1][0].item()
      instance.setVariableUInt("x_a", int(x))
      instance.setVariableUInt("y_a", int(y))
      instance.setVariableUInt("grid_index", int(x * ENV_MAX + y))
      if USE_VISUALISATION:
        instance.setVariableFloat("x", float(x))
        instance.setVariableFloat("y", float(y))
      instance.setVariableFloat("energy", random.uniform(1, MAX_INIT_ENERGY))
      # select agent strategy
      agent_trait: int = random.choice(AGENT_TRAITS)
      instance.setVariableUInt("agent_trait", agent_trait)
      # select agent strategy
      if AGENT_STRATEGY_PER_TRAIT:
        # if we are using a per-trait strategy, then pick random weighted strategies
        instance.setVariableArrayUInt('agent_strategies', random.choices(AGENT_STRATEGIES, weights=AGENT_WEIGHTS, k=len(AGENT_TRAITS)))
      else:
        # otherwise, we need a strategy for agents with matching traits
        # and a second for agents with different traits
        strategy_my: int
        strategy_other: int
        strategy_my, strategy_other = random.choices(AGENT_STRATEGIES, weights=AGENT_WEIGHTS, k=2)
        agent_strategies: list = []
        trait: int
        for i, trait in enumerate(agent_trait):
          if trait == agent_trait:
            agent_strategies.append(strategy_my)
          else:
            agent_strategies.append(strategy_other)
        instance.setVariableArrayUInt('agent_strategies', agent_strategies)
    del x, y, grid, np
    # Set the population for the simulation object
    simulation.setPopulationData(population)

  simulation.simulate()
  # Potentially export the population to disk
  # simulation.exportData("end.xml")
  # If visualisation is enabled, end the visualisation
  if pyflamegpu.VISUALISATION:
      visualisation.join()
  
if __name__ == "__main__":
    main()