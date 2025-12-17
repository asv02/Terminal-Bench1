A network engineer is analyzing log files from a legacy data transmission system. The system sends data packets as a stream of integers. Due to old hardware, the packets sometimes arrive out of order.

The engineer defines a specific type of error called a "sequence disturbance." A sequence disturbance occurs within a specific window of time when a packet that arrived earlier has a higher value than a packet that arrived later.

The engineer needs to find the most stable window of transmission. To do this, they must analyze the stream using a sliding window of a fixed size k. For every possible window of size k in the stream, they need to count the total number of sequence disturbances.

The goal is to find the minimum number of disturbances possible in any window of that duration.

The input data is located in /app/transmission_logs.json. The file contains a list of transmission sessions. Each session has:

id: A unique identifier for the session.
stream: The array of integers representing the packet sequence.
window_size: The integer k representing the duration to analyze.

For each session, the program must calculate the minimum disturbance count among all subarrays of length k.

The results must be written to /app/stability_report.txt. Each line should contain the session id followed by a space and the calculated minimum count. The lines must be sorted alphabetically by the session id.