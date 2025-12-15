In the old hill country lies a circular village where each household sits along a ring road around the central well. Every household keeps a resource balance representing its current food or supply surplus. A rare situation has occurred: at most one household has fallen into deficit, causing concerns that the shortage could spread across the community.

To restore stability, villagers may pass resources to their neighbors. Because the homes are arranged in a perfect circle, the left neighbor of house 0 is house n-1, and the right neighbor of house n-1 is house 0.

## Task Objective

Your task is to determine the absolute minimum effort cost required to clear the deficit based on the village's resource laws.

The cost is determined by the following rules:

1.  Transport Cost: Moving `K` units of resources over a distance of `D` houses incurs a cost of `K × D`.
2.  Optimization Constraint: To minimize the total cost, resources must always be sourced from the nearest households with a surplus.
3.  Topology: Distance `D` is measured as the shortest path along the ring (checking both clockwise and counter-clockwise).

If it is impossible to rescue the village from the deficit (i.e., the total sum of resources in the village is negative), the answer is -1.

## Input File Specification

All village configurations are provided in a JSON file named `/app/cargo_balance.json`.

The structure of this file is:

```json
{
  "scenarios": [
    {
      "id": "<string>",
      "balance": [<int>, <int>, ...]
    },
    ...
  ]
}
```

  - Each element inside the "scenarios" list describes a single ring of houses.
  - The field "id" uniquely identifies the scenario.
  - "balance" contains the net resources of each house in the circular arrangement.

## Output File Specification

For each scenario, compute the minimum number of moves required using the logic above and write the results into a file named `/app/cargo_report.txt`.

Each line must contain scenario\_id followed by a space and the computed minimum move count.

Lines must appear in alphabetical order of scenario\_id.

## Note

Some rings contain many households, and the village elders have limited time before spoilage affects the stored food. A slow, step-by-step simulation of each individual transfer will not finish in time. You must determine the minimum move count using a method that remains efficient even for very large rings.