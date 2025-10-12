# ==============================================================================
#                      PARAMETER LIBRARY GENERATION SCRIPT
# ==============================================================================
#
# Purpose:
# This script is the primary tool for building the "parameter library." Its goal
# is to find the optimal set of underlying model parameters (`mu`, `sigma`, `kappa`)
# that produce a wide range of predefined market scenarios.
#
# How it works:
# 1. It defines a grid of target scenarios, each with a specific target for
#    mean annual return and price spread (95th percentile - 5th percentile).
# 2. For each scenario, it uses the `differential_evolution` optimizer to
#    run a "goal-seeking" process. The optimizer tests different combinations
#    of `mu`, `sigma`, and `kappa` until it finds the set that best matches
#    the target mean and spread.
# 3. The process is incremental and persistent. It saves its progress to a
#    `param_library.csv` file after each scenario is optimized. If the script
#    is stopped and restarted, it will automatically resume where it left off.
# 4. It leverages parallel processing (`multiprocessing`) to significantly
#    speed up the computationally intensive optimization step.
#
# The final output is a comprehensive CSV file mapping each market scenario
# to the optimal parameters needed to generate it. This library is the
# foundation for generating the final, large set of simulated paths.
#
# ==============================================================================

import numpy as np
import pandas as pd
import time
import os
from scipy.optimize import differential_evolution
from multiprocessing import cpu_count

# ==============================================================================
#                      MODEL FUNCTIONS
# ==============================================================================

def generate_tanh_ou_path(days, mu, sigma, kappa, beta, S0=1):
    """Generates a baseline path using a tanh-based OU process."""
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

def apply_tanh_damping(drop_frac, current_drawdown, threshold=0.5, cap=0.65, alpha=70):
    """Applies a damping factor to a shock."""
    if current_drawdown < threshold: return drop_frac
    if current_drawdown >= cap: return 0.0
    return drop_frac * 0.5 * (1 - np.tanh(alpha * (current_drawdown - threshold)))

def objective_function(params_to_optimize, fixed_params, target_mean, target_spread):
    """
    Loss function for the optimizer.
    """
    mu, sigma, kappa = params_to_optimize
    n_paths = 25
    final_returns = []
    final_prices_at_end = []
    
    for _ in range(n_paths):
        all_params = list(params_to_optimize) + fixed_params
        mu, sigma, kappa, beta, minor_yrs, major_yrs, k, gamma, rec_var = all_params
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
        peak_price = base_price_path[0]
        for t, typ in events:
            price_before_shock = base_price_path[t] * cumulative_shock[t]
            peak_price = max(peak_price, price_before_shock)
            current_drawdown = 1 - (price_before_shock / peak_price)

            if typ == 'minor':
                drop, d_days, r_days = np.random.uniform(0.2,0.35), np.random.randint(20,70), np.random.randint(300,1000)
            else:
                drop, d_days, r_days = np.random.uniform(0.4,0.6), np.random.randint(40,120), np.random.randint(1000,2500)
            
            damped_drop = apply_tanh_damping(drop, current_drawdown)
            
            rec_target = np.random.uniform(1 - rec_var, 1 + rec_var)
            dislocation = simulate_dislocation(days_long + 1 - t, damped_drop, d_days, r_days, recovery_target=rec_target)
            cumulative_shock[t:] *= dislocation
            
        raw_prices = base_price_path * cumulative_shock
        path_final_prices = apply_return_capping(raw_prices, gamma=gamma)
        
        final_returns.append((path_final_prices[-1] / path_final_prices[0])**(1/years) - 1)
        final_prices_at_end.append(path_final_prices[-1])

    actual_mean = np.mean(final_returns)
    p95 = np.percentile(final_prices_at_end, 95)
    p5 = np.percentile(final_prices_at_end, 5)
    actual_spread = (p95 - p5) / np.mean(final_prices_at_end)
    
    mean_error = ((actual_mean - target_mean) / 0.01)**2
    spread_error = ((actual_spread - target_spread) / 0.1)**2
    loss = mean_error + spread_error
    
    return loss

def create_or_update_parameter_library(target_scenarios, filename="param_library.csv"):
    """
    Runs the optimizer for each scenario to find the best parameters.
    Saves progress to a CSV and only computes missing scenarios.
    """
    if os.path.exists(filename):
        param_library_df = pd.read_csv(filename)
        print(f"Existing parameter library found with {len(param_library_df)} entries.")
    else:
        param_library_df = pd.DataFrame(columns=['target_mean', 'target_spread', 'opt_mu', 'opt_sigma', 'opt_kappa'])
        print("No parameter library found. Creating a new one.")

    fixed_params = [4.724, 14.338, 33.129, 8.701, 13.726, 0.118]
    optimization_bounds = [(0.03, 0.10), (0.12, 0.25), (0.5, 4.0)]

    scenarios_to_run = []
    
    if not param_library_df.empty:
        for scenario in target_scenarios:
            is_done = np.any(
                (np.isclose(param_library_df['target_mean'], scenario['mean'])) &
                (np.isclose(param_library_df['target_spread'], scenario['spread']))
            )
            if not is_done:
                scenarios_to_run.append(scenario)
    else:
        scenarios_to_run = target_scenarios
    
    if not scenarios_to_run:
        print("All target scenarios are already in the library. Nothing to do.")
        return param_library_df

    print(f"Total scenarios to calculate: {len(scenarios_to_run)}")
    start_time = time.time()

    for scenario_num, scenario in enumerate(scenarios_to_run):
        iter_start_time = time.time()
        print(f"\n--- Optimizing for Scenario {scenario_num+1}/{len(scenarios_to_run)}: Target Mean={scenario['mean']:.2%}, Spread={scenario['spread']:.1%} ---")
        
        # --- EFFICIENCY IMPROVEMENT: Re-enable parallel processing ---
        result = differential_evolution(
            objective_function, optimization_bounds,
            args=(fixed_params, scenario['mean'], scenario['spread']),
            maxiter=15, popsize=10, tol=0.01, disp=True, 
            updating='deferred',
            workers=cpu_count() # Use all available CPU cores
        )
        
        best_mu, best_sigma, best_kappa = result.x
        iter_end_time = time.time()
        print(f"--- Optimal Parameters Found in {iter_end_time - iter_start_time:.1f} seconds: mu={best_mu:.3f}, σ={best_sigma:.3f}, κ={best_kappa:.2f} ---")
        
        new_row = pd.DataFrame([{'target_mean': scenario['mean'], 'target_spread': scenario['spread'], 'opt_mu': best_mu, 'opt_sigma': best_sigma, 'opt_kappa': best_kappa}])
        param_library_df = pd.concat([param_library_df, new_row], ignore_index=True)
        
        param_library_df.to_csv(filename, index=False)
        print(f"Progress saved to '{filename}'. Total entries: {len(param_library_df)}")

    total_time = time.time() - start_time
    print(f"\nOptimization of new scenarios completed in {total_time / 60:.2f} minutes.")
    return param_library_df

# ==============================================================================
#                                  EXECUTION
# ==============================================================================
if __name__ == '__main__':
    # --- FULL EXECUTION MODE ---
    # This script is designed to be run from the command line for long periods.
    print("--- FULL EXECUTION MODE ---")
    target_scenarios = []
    for mean_return in np.arange(0.04, 0.091, 0.005):
        for spread_pct in np.arange(1.0, 3.01, 0.25):
            target_scenarios.append({'mean': mean_return, 'spread': spread_pct})
    
    print(f"Defined {len(target_scenarios)} unique scenarios for the parameter map.")

    param_library_df = create_or_update_parameter_library(target_scenarios)
    
    print("\n--- Final Parameter Library ---")
    print(param_library_df)
