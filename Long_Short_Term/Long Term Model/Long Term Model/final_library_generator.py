# ==============================================================================
#                      FINAL PATH LIBRARY GENERATOR
# ==============================================================================
#
# Purpose:
# This script represents the final step of the long-term path generation model.
# It orchestrates a two-step process to create a large, comprehensive library
# of simulated path statistics.
#
# How it works:
# 1.  Create/Update a Parameter Library: It first runs a "goal-seeking"
#     optimizer for a wide grid of target scenarios (mean return and spread).
#     The result is a CSV file (`param_library.csv`) that maps each target
#     scenario to the optimal model parameters (`mu`, `sigma`, `kappa`)
#     needed to produce it. This process is incremental and persistent.
#
# 2.  Generate the Final Statistics Library: Using the pre-computed parameter
#     library, it then generates ~5,000 "well-behaved" paths. For each path,
#     it calculates a final set of key statistics and saves them to a
#     DataFrame. This final table is the main deliverable.
#
# This two-step approach is highly efficient, as the computationally expensive
# optimization is performed only once and its results are reused.
#
# ==============================================================================

import numpy as np
import pandas as pd
import time
import os
from scipy.optimize import differential_evolution
from multiprocessing import Pool, cpu_count

# ==============================================================================
#                      MODEL FUNCTIONS (FINAL VERSION)
# ==============================================================================

def generate_tanh_ou_path(days, mu, sigma, kappa, beta, S0=1):
    """Generates a baseline path using a tanh-based Ornstein-Uhlenbeck (OU) process."""
    dt = 1 / 252
    log_S0 = np.log(S0)
    X = log_S0
    path = [X]
    for i in range(days):
        t = (i + 1) * dt
        target_mu_t = log_S0 + mu * t
        reversion_force = -kappa * np.tanh(beta * (X - target_mu_t)) * dt
        random_shock = sigma * np.sqrt(dt) * np.random.randn()
        X += reversion_force + random_shock
        path.append(X)
    return np.array(path)

def apply_return_capping(prices, gamma):
    """Applies a soft cap to daily returns."""
    if gamma <= 0: return prices
    safe_prices = np.maximum(prices, 1e-9)
    log_returns = np.diff(np.log(safe_prices))
    capped_log_returns = (1 / gamma) * np.tanh(gamma * log_returns)
    new_prices = np.zeros_like(prices)
    new_prices[0] = prices[0]
    new_prices[1:] = prices[0] * np.exp(np.cumsum(capped_log_returns))
    return new_prices

def simulate_dislocation(total_days, drop_frac, drop_days, rec_days, shape_k=10, recovery_target=1.0):
    """Generates a crisis shock envelope with a variable recovery target."""
    if drop_days <= 0 or rec_days <= 0: return np.ones(total_days)
    decline, recov = np.arange(drop_days), np.arange(rec_days)
    L = lambda x, d: 1/(1 + np.exp(-shape_k * (x/d - 0.5))) if d > 0 else np.zeros_like(x)
    decline_factor = 1 - drop_frac * L(decline, drop_days)
    start_of_recovery = 1 - drop_frac
    end_of_recovery = recovery_target
    recovery_range = end_of_recovery - start_of_recovery
    recovery_factor = start_of_recovery + recovery_range * L(recov, rec_days)
    shock = np.concatenate([decline_factor, recovery_factor])
    full = np.ones(total_days)
    n = min(len(shock), total_days)
    full[:n] = shock[:n]
    return full

def generate_clustered_crisis_events(days, base_minor_rate, base_major_rate, k=12, boost_period=2000, cooldown_period=756):
    """Generates crisis events with clustering and a full cooldown period."""
    events = []
    boosted_minor_until, boosted_major_until, major_cooldown_until = -1, -1, -1
    for day in range(days):
        minor_rate_today = base_minor_rate * (k if day < boosted_minor_until else 1.0)
        major_rate_today = base_major_rate * (k if day < boosted_major_until else 1.0)
        if day < major_cooldown_until:
            major_rate_today, minor_rate_today = 0.0, 0.0
        if np.random.rand() < minor_rate_today:
            events.append((day, 'minor'))
            boosted_minor_until = day + boost_period
        if np.random.rand() < major_rate_today:
            events.append((day, 'major'))
            boosted_major_until = day + boost_period
            major_cooldown_until = day + cooldown_period
    return sorted(events)

def count_lost_periods(prices, period_length_years):
    """Counts the number of distinct lost periods of a given length."""
    period_length_days = int(period_length_years * 252)
    if len(prices) < period_length_days: return 0
    highs = np.maximum.accumulate(prices)
    count = 0
    i = 0
    while i <= len(prices) - period_length_days:
        peak = highs[i]
        if prices[i] < peak:
            if not np.any(prices[i : i + period_length_days] >= peak):
                count += 1
                i += period_length_days
            else:
                i += 1
        else:
            i += 1
    return count

# ==============================================================================
#                      OPTIMIZATION & LIBRARY GENERATION
# ==============================================================================

def run_single_path_for_objective(args):
    """Helper function for parallel optimization. Runs a single path and returns its final return and price."""
    mu, sigma, kappa, beta, minor_yrs, major_yrs, k, gamma, rec_var, seed = args
    np.random.seed(seed)
    years, days_long = 40, 40 * 252
    ou_path = generate_tanh_ou_path(days_long, mu, sigma, kappa, beta)
    base_price_path = np.exp(ou_path)
    base_minor_rate = 1 / (minor_yrs * 252)
    base_major_rate = 1 / (major_yrs * 252)
    events = generate_clustered_crisis_events(days_long, base_minor_rate, base_major_rate, k)
    guaranteed_crisis_day = np.random.randint(252, 252 * 5)
    events.append((guaranteed_crisis_day, 'minor'))
    events = sorted(list(set(events)))
    cumulative_shock = np.ones(days_long + 1)
    for t, typ in events:
        if typ == 'minor':
            drop, d_days, r_days = np.random.uniform(0.2,0.35), np.random.randint(20,70), np.random.randint(300,1000)
        else:
            drop, d_days, r_days = np.random.uniform(0.4,0.6), np.random.randint(40,120), np.random.randint(1000,2500)
        rec_target = np.random.uniform(1 - rec_var, 1 + rec_var)
        dislocation = simulate_dislocation(days_long + 1 - t, drop, d_days, r_days, recovery_target=rec_target)
        cumulative_shock[t:] *= dislocation
    raw_prices = base_price_path * cumulative_shock
    path_final_prices = apply_return_capping(raw_prices, gamma=gamma)
    return (path_final_prices[-1] / path_final_prices[0])**(1/years) - 1, path_final_prices[-1]

def objective_function(params_to_optimize, fixed_params, target_mean, target_spread):
    """Loss function for the optimizer."""
    mu, sigma, kappa = params_to_optimize
    n_paths = 25
    final_returns = []
    final_prices_at_end = []
    for _ in range(n_paths):
        all_params = list(params_to_optimize) + fixed_params
        ret, price = run_single_path_for_objective(all_params + [np.random.randint(1e6)])
        final_returns.append(ret)
        final_prices_at_end.append(price)
    actual_mean = np.mean(final_returns)
    p95 = np.percentile(final_prices_at_end, 95)
    p5 = np.percentile(final_prices_at_end, 5)
    actual_spread = (p95 - p5) / np.mean(final_prices_at_end)
    mean_error = ((actual_mean - target_mean) / 0.01)**2
    spread_error = ((actual_spread - target_spread) / 0.1)**2
    return mean_error + spread_error

def create_parameter_library(target_scenarios, filename="param_library.csv"):
    """
    STEP 1: Runs the optimizer for each scenario to find the best parameters.
    """
    if os.path.exists(filename):
        param_library_df = pd.read_csv(filename)
        print(f"Existing parameter library found with {len(param_library_df)} entries.")
    else:
        param_library_df = pd.DataFrame(columns=['target_mean', 'target_spread', 'opt_mu', 'opt_sigma', 'opt_kappa'])
        print("No parameter library found. Creating a new one.")

    fixed_params = [4.724, 14.338, 33.129, 8.701, 13.726, 0.118]
    optimization_bounds = [(0.03, 0.10), (0.12, 0.25), (0.5, 4.0)]
    scenarios_to_run = [s for s in target_scenarios if not np.any((np.isclose(param_library_df['target_mean'], s['mean'])) & (np.isclose(param_library_df['target_spread'], s['spread'])))]
    
    if not scenarios_to_run:
        print("All target scenarios are already in the library.")
        return param_library_df

    print(f"Total new scenarios to calculate: {len(scenarios_to_run)}")
    
    for scenario in scenarios_to_run:
        print(f"\n--- Optimizing for Scenario: Target Mean={scenario['mean']:.2%}, Spread={scenario['spread']:.1%} ---")
        result = differential_evolution(
            objective_function, optimization_bounds,
            args=(fixed_params, scenario['mean'], scenario['spread']),
            maxiter=15, popsize=10, tol=0.01, disp=True, updating='deferred', workers=cpu_count()
        )
        best_mu, best_sigma, best_kappa = result.x
        new_row = pd.DataFrame([{'target_mean': scenario['mean'], 'target_spread': scenario['spread'], 'opt_mu': best_mu, 'opt_sigma': best_sigma, 'opt_kappa': best_kappa}])
        param_library_df = pd.concat([param_library_df, new_row], ignore_index=True)
        param_library_df.to_csv(filename, index=False)
        print(f"Progress saved to '{filename}'. Total entries: {len(param_library_df)}")
    return param_library_df

def generate_final_statistics_library(param_df, total_library_size=5000):
    """
    STEP 2: Uses the pre-computed parameter library to generate the final
    set of path statistics efficiently.
    """
    final_stats = []
    if len(param_df) == 0: return pd.DataFrame()
    n_paths_per_scenario = int(np.ceil(total_library_size / len(param_df)))
    fixed_params = [4.724, 14.338, 33.129, 8.701, 13.726, 0.118]

    for _, row in param_df.iterrows():
        print(f"\n--- Generating {n_paths_per_scenario} paths for target mean {row['target_mean']:.2%} ---")
        path_params = [row['opt_mu'], row['opt_sigma'], row['opt_kappa']] + fixed_params
        
        scenario_paths = []
        for i in range(n_paths_per_scenario):
            # Run simulation
            mu, sigma, kappa, beta, minor_yrs, major_yrs, k, gamma, rec_var = path_params
            years, days_long = 40, 40 * 252
            ou_path = generate_tanh_ou_path(days_long, mu, sigma, kappa, beta)
            base_price_path = np.exp(ou_path)
            base_minor_rate = 1 / (minor_yrs * 252); base_major_rate = 1 / (major_yrs * 252)
            events = generate_clustered_crisis_events(days_long, base_minor_rate, base_major_rate, k)
            guaranteed_crisis_day = np.random.randint(252, 252 * 5)
            events.append((guaranteed_crisis_day, 'minor')); events = sorted(list(set(events)))
            cumulative_shock = np.ones(days_long + 1)
            for t, typ in events:
                if typ == 'minor': drop, d_days, r_days = np.random.uniform(0.2,0.35), np.random.randint(20,70), np.random.randint(300,1000)
                else: drop, d_days, r_days = np.random.uniform(0.4,0.6), np.random.randint(40,120), np.random.randint(1000,2500)
                rec_target = np.random.uniform(1 - rec_var, 1 + rec_var)
                dislocation = simulate_dislocation(days_long + 1 - t, drop, d_days, r_days, recovery_target=rec_target)
                cumulative_shock[t:] *= dislocation
            raw_prices = base_price_path * cumulative_shock
            final_prices = apply_return_capping(raw_prices, gamma=gamma)
            
            # Filter out unreasonable paths
            max_drop = 1 - np.min(final_prices / np.maximum.accumulate(final_prices))
            lost_decades = count_lost_periods(final_prices, 10)
            if max_drop <= 0.75 and lost_decades <= 2:
                scenario_paths.append(final_prices)

        if not scenario_paths: continue
        
        # Calculate scenario-wide stats
        final_prices_at_end = [p[-1] for p in scenario_paths]
        scenario_p05 = np.percentile(final_prices_at_end, 5)
        scenario_p95 = np.percentile(final_prices_at_end, 95)
        actual_spread = (scenario_p95 - scenario_p05) / np.mean(final_prices_at_end)

        for path in scenario_paths:
            stats = {
                "path_id": len(final_stats),
                "target_mean": row['target_mean'],
                "target_spread": row['target_spread'],
                "actual_annual_return": (path[-1]/path[0])**(1/40)-1,
                "actual_spread": actual_spread,
                "scenario_p05_price": scenario_p05,
                "scenario_p95_price": scenario_p95,
                "max_drop": 1 - np.min(path / np.maximum.accumulate(path)),
                "lost_decades": count_lost_periods(path, 10)
            }
            final_stats.append(stats)
            
    return pd.DataFrame(final_stats)

# ==============================================================================
#                                  EXECUTION
# ==============================================================================
if __name__ == '__main__':
    # Define the grid of scenarios to create the parameter library
    target_scenarios = []
    for mean_return in np.arange(0.04, 0.091, 0.005):
        for spread_pct in np.arange(1.0, 3.01, 0.25):
            target_scenarios.append({'mean': mean_return, 'spread': spread_pct})
    print(f"Defined {len(target_scenarios)} unique scenarios for the parameter map.")

    # STEP 1: Create/Update the parameter library
    param_library_df = create_parameter_library(target_scenarios)
    
    # STEP 2: Generate the final path statistics library
    final_path_library_df = generate_final_statistics_library(param_library_df, total_library_size=5000)
    
    print("\n--- Sample of Final Path Statistics Library ---")
    if not final_path_library_df.empty:
        # Save the final library to a CSV file
        output_filename = "final_path_statistics_library.csv"
        final_path_library_df.to_csv(output_filename, index=False)
        print(f"\nLibrary successfully saved to '{output_filename}'")
        
        # Display a sample of the generated DataFrame in the console
        print("\n--- First 5 rows of the generated library ---")
        print(final_path_library_df.head())
    else:
        print("No valid paths were generated to create the final library.")