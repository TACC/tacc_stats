#include <mpi.h>
#include <stdio.h>
#include <stdlib.h>

int main(int argc, char** argv) {
  // Initialize the MPI environment
  MPI_Init(NULL, NULL);
  // Find out rank, size
  int world_rank;
  MPI_Comm_rank(MPI_COMM_WORLD, &world_rank);
  int world_size;
  MPI_Comm_size(MPI_COMM_WORLD, &world_size);

  // We are assuming at least 2 processes for this task
  if (world_size < 2) {
    fprintf(stderr, "World size must be greater than 1 for %s\n", argv[0]);
    MPI_Abort(MPI_COMM_WORLD, 1);
  }

  int N = 1024*1024*10;
  double number[N];
  int i;
  if (world_rank == 0) {
    // If we are rank 0, set the number to -1 and send it to process 1
    for (i = 0; i < N; i++) number[i] = i;
    MPI_Send(&number, N, MPI_DOUBLE, 1, 0, MPI_COMM_WORLD);
    MPI_Recv(&number, N, MPI_DOUBLE, 1, 0, MPI_COMM_WORLD, MPI_STATUS_IGNORE);
  } else if (world_rank == 1) {
    MPI_Recv(&number, N, MPI_DOUBLE, 0, 0, MPI_COMM_WORLD, MPI_STATUS_IGNORE);
    MPI_Send(&number, N, MPI_DOUBLE, 0, 0, MPI_COMM_WORLD);
    printf("Process 1 received number %d from process 0\n", number[5]);
  }
  MPI_Finalize();
}
