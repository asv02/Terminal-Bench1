Far out in deep space, a chain of damaged research stations drifts in silence.  
Each station contains a sequence of unstable compartments. Entering a compartment drains your oxygen supply, and only if your remaining oxygen is above the compartment’s stability threshold do you successfully stabilize it and earn a point.

Your mission log contains several gauntlet runs that must be analyzed.  
Each run begins with a certain oxygen amount and a list of compartments.  
For compartment i:

1. Entering it reduces your oxygen by damage[i].
2. After the reduction, if your oxygen is still at least requirement[i], you earn 1 point.

You always traverse the compartments in order without skipping any.  
Even if your oxygen becomes zero or negative, you must continue through the remaining compartments.

For each run, define score(j) to be the number of points earned if you begin with the given oxygen and start from compartment j, then proceed forward to the last one.

Your task is to compute, for every gauntlet run, the total value

score(1) + score(2) + ... + score(n)

where n is the number of compartments in that run.

All gauntlet runs are listed in a file named /app/gauntlet_scenarios.json.  
Each entry contains:

id: a unique identifier  
hp: starting oxygen  
damage: the oxygen drain per compartment  
requirement: the stability threshold per compartment

You must read all scenarios, compute the correct total score for each one, and write the results into a file named /app/gauntlet_report.txt.

Each line of /app/gauntlet_report.txt must contain:

scenario_id + space + total_score_value

The lines must appear in alphabetical order of scenario_id.

The puzzle is solved when /app/gauntlet_report.txt exists and contains the correct results.

Because of the drifting stations' instability and the limited time before their power cores collapse, your calculations must be carried out in an efficient, well-optimized manner.  
A slow or repeatedly restarted simulation will not complete before the stations break apart, so you must determine the total scores using a method that handles large runs without unnecessary recomputation.
