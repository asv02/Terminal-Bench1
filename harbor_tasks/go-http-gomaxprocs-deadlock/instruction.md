Reproduce and demonstrate a deterministic deadlock in a Go HTTP server
that occurs only under specific GOMAXPROCS values and concurrent request
patterns.

You must produce exactly the following artifacts:

- One Go source file named `server.go`
- One reproduction document named `REPRO.md`

--- Go program requirements ---

The file `server.go` must:

1. Be a single, self-contained Go source file.
2. Start an HTTP server using the standard `net/http` package and the
   `http.ListenAndServe` function.
3. Explicitly set the runtime scheduler using:
   runtime.GOMAXPROCS(1).
4. Contain a real deadlock caused by synchronization primitives
   (e.g., mutex ordering or channel dependency cycles),
   not by infinite loops, sleeps, or busy-waiting.
5. Expose at least two HTTP endpoints implemented as handler functions
   named `handlerA` and `handlerB` such that:
   - The program must define exactly two mutex variables named `muA` and `muB`.
   - `handlerA` must acquire mutex `muA` and then mutex `muB`.
   - `handlerB` must acquire mutex `muB` and then mutex `muA`.

   - When the endpoints are hit concurrently under GOMAXPROCS=1,
     the program deadlocks deterministically due to this lock-order
     inversion.
   - The same program does NOT deadlock under higher GOMAXPROCS values
     (e.g., GOMAXPROCS=2 or greater).
   - With GOMAXPROCS=1, the Go scheduler runs all goroutines on a single OS thread, making lock-order inversion deterministic when concurrent requests interleave. With GOMAXPROCS>1, goroutines may execute in parallel on multiple threads, allowing one handler to complete both lock acquisitions before the other blocks, preventing a deterministic deadlock.

Nondeterministic timing tricks (e.g., time.Sleep-based deadlocks)
are explicitly forbidden.

The deadlock must be explainable purely via synchronization ordering
and Go runtime scheduling behavior, using valid Go coordination
mechanisms such as mutexes, channels, or sync.WaitGroup.


--- Reproduction documentation requirements ---
  
The file `REPRO.md` must document, in plain text:

1. The exact Go version used.
2. The operating system and architecture.
3. The value of GOMAXPROCS used during reproduction
   (including use of the environment variable GOMAXPROCS=1).
4. The exact commands required to reproduce the deadlock, including
   at least one example using a command-line HTTP client
   (e.g., curl) to issue concurrent requests.
5. Clear instructions that result in a deterministic deadlock.

--- Deadlock evidence requirements ---

The reproduction documentation must include evidence of the deadlock,
including:

- Evidence of the deadlock via a goroutine dump or an equivalent
  Go diagnostic mechanism (e.g., SIGQUIT / Ctrl+\ / kill -QUIT),
  showing goroutines blocked on synchronization primitives.
- At least one valid Go deadlock diagnostic mechanism, such as:
  - the Go race detector, or
  - a pprof blocking profile.

The documentation must explicitly reference goroutines and the
deadlock state in the captured evidence.

--- Scope clarification ---

The task is to demonstrate and document a reproducible deadlock.
Automated tests are not required to detect the deadlock at runtime;
correctness is evaluated based on the produced program structure,
documented reproduction steps, and included diagnostic evidence.

--- Constraints ---

- Exactly one Go source file (`server.go`) must be produced.
- Exactly one documentation file (`REPRO.md`) must be produced.
- No external dependencies.
- No network access beyond the local HTTP server.
- The deadlock must be deterministic and reproducible as documented.
