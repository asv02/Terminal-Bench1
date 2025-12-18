The lead engineer at the Helios Fusion Plant is monitoring the stability of the reactor's containment field. The field is maintained by a series of magnetic coils, each vibrating at a specific frequency (an integer).

For maximum efficiency and safety, each coil must be tuned to a "Harmonic Frequency." A frequency is considered Harmonic if its binary representation (without leading zeros) reads the same forwards and backwards.

However, due to thermal fluctuations, the coils often drift from their ideal states. The engineer must manually adjust the frequency of each coil to the nearest Harmonic Frequency.

The cost of adjustment is linear: changing a frequency by 1 unit consumes 1 megajoule of energy. The engineer needs to calculate the minimum energy required to stabilize each coil individually.

The current status of the reactor coils is stored in `/app/reactor_status.json`.
The file contains a JSON object with a top-level key `scenarios`, which holds a list of sector entries.

Each entry in this list contains:
- `id`: A unique identifier for the sector.
- `frequencies`: A list of integers representing the current frequency of each coil in that sector.

Your task is to compute the minimum adjustment cost for each coil in a sector and sum them up to get the total stabilization cost for that sector.

The results must be written to `/app/stabilization_costs.txt`.
Each line must contain:
`sector_id` + space + `total_cost`

The lines must be sorted alphabetically by `sector_id`.

Clarifications:
* Leading Zeros: The binary representation is calculated without leading zeros. For example, the integer `4` is represented as `100`. Since `100` backwards is `001`, it is not a palindrome.
* Zero Case: The integer `0` (binary `0`) is considered a valid binary palindrome.
* Equidistant Case: If a frequency is exactly equidistant from two Harmonic Frequencies, the adjustment cost is identical. You may use the distance to either target.