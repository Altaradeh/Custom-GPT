# **README: Long-Term Market Path Simulation Model**

## **1\. Overview**

This project provides a sophisticated stochastic model for generating realistic, 40-year synthetic price paths for financial assets. The core objective is to create simulations that adhere to a specific set of statistical targets, including long-term annual returns, volatility, maximum drawdowns, and the frequency of market crises.

To overcome the challenge of parameter entanglement, the model is built on a decoupled, multi-layered architecture that provides more orthogonal control over the final path characteristics.

## **2\. The Two-Step Workflow**

Generating thousands of paths that meet specific outcome targets (e.g., a specific mean return and spread) is computationally expensive. A brute-force approach would be highly inefficient.

Therefore, we use an optimized two-step workflow:

1. **Build a Parameter Map:** First, we run a "goal-seeking" optimizer to find the ideal model parameters (`mu`, `sigma`, `kappa`) for a wide grid of target scenarios. This is the slow, computationally intensive step. The result is a small but critical file, `param_library.csv`, which acts as a "map" from a desired outcome to the settings that produce it.  
2. **Generate the Path Statistics Library:** Once the parameter map is created, we can use it to very quickly and efficiently generate the final, massive library of \~5,000 path statistics. This script simply looks up the required parameters from the map and runs the simulations.

   ## **3\. File Descriptions & Usage**

This project contains four key scripts, designed to be run locally as part of a pipeline that will eventually be containerized (Dockerized).

### **a) `optimized_search_parameters.py` (The Parameter Map Builder)**

* **Purpose:** This is the main script for the computationally intensive task of building the **parameter library**. It runs the goal-seeking optimizer for each target scenario.  
* **Key Features:**  
  * **Incremental & Persistent:** Saves its progress to `param_library.csv` after each scenario. It can be stopped and restarted without losing work.  
  * **Parallelized:** Utilizes `multiprocessing` to leverage all available CPU cores.  
* **How to Use:** Run this script from your terminal (`python optimized_search_parameters.py`). This is intended for long-running sessions to build the complete parameter map.

  ### **b) `final_library_generator.py` (The Path Library Builder)**

* **Purpose:** This script uses the `param_library.csv` generated in the previous step to produce the **final, massive library of path statistics**.  
* **Output:** A large table (e.g., 5,000+ rows) containing the detailed statistics for each "well-behaved" path, ready to be consumed by the main application.  
* **How to Use:** Once `param_library.csv` is complete, run this script from your terminal to generate the final deliverable.

  ### **c) `long_term_path_simulator.py` (The Scenario Viewer)**

* **Purpose:** A lightweight tool for **visualizing and validating a single, specific scenario** using a set of parameters from the `param_library.csv`.  
* **Output:** A statistical dashboard and an envelope plot for the chosen parameter set.  
* **How to Use:** Modify the `calibrated_params` dictionary at the bottom of the script and run it from your terminal.

  ### **d) `interactive_envelope_simulator.ipynb` (The Sandbox/Development Tool)**

* **Purpose:** An interactive Jupyter Notebook for **manual calibration, exploration, and scenario analysis**. It is a development tool, not part of the final production pipeline.  
* **How to Use:** Open in a Jupyter environment and run all cells to use the interactive sliders.

  ## **4\. Recommended Workflow**

1. **Build the Parameter Library:** Run `optimized_search_parameters.py` from your terminal. This is the main, time-consuming step. Let it run until it has processed all the defined scenarios.  
2. **Generate the Final Data:** Run `final_library_generator.py` to create the large table of path statistics. This is the primary deliverable.  
3. **Validate & Visualize (As Needed):** Use `long_term_path_simulator.py` to inspect the results for any specific scenario from your parameter library.

   ## **5\. Dependencies**

This project requires the following Python libraries:

* `numpy`  
* `pandas`  
* `matplotlib`  
* `scipy`  
* `ipywidgets` (for the interactive notebook)


