A catastrophic data corruption event has struck the central archives of the Nexus mainframe. The storage sectors are destabilizing, and critical encryption keys have been shattered into fragmented data shards. The system's automated recovery daemon has failed, and manual intervention is required to reconstruct the keys before the data is lost to the void.

The recovered data is represented as a stream of shards, where each shard is a two-character alphanumeric code. To reconstruct a valid key, the system must fuse two compatible shards together. **Crucially, this fusion process consumes the source data—each shard can be used exactly once and cannot be reused to form multiple keys.**

The restoration protocol relies on strict parity rules. The system has identified a specific signature byte for each data batch. For two shards to successfully fuse into a key, they must meet two conditions. First, both shards must contain the batch's specific signature byte. Second, the two shards must differ in exactly one position. If the shards are identical or differ in both positions, the fusion fails and the data is rejected.

For instance, if the signature byte is "a", shards "ab" and "ac" will fuse because they both contain "a" and differ only at the second position. Shards "aa" and "ba" would also fuse. However, "ab" and "ba" cannot fuse because they differ at both positions.

The corrupted sectors are accessible via /app/restoration_batches.json. This file contains the list of recovery batches. Each entry provides a unique batch ID, the pool of available shards, and the required signature byte for that specific sector.

The objective is to process every batch and calculate the maximum number of keys that can be reconstructed using optimal fusion strategies. These totals must be written to a report file at /app/restoration_report.txt. Each line of the report must contain the batch ID followed by the maximum number of keys, separated by a space. The entries in the report must be sorted alphabetically by the batch ID.

The corruption is spreading across the drive sectors rapidly, so time is of the essence. The task is complete only when the report file exists and contains the correct values for all batches.