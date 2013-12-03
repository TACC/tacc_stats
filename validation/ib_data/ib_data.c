#include "mpi.h"

// Check job 1811373

#define MCW MPI_COMM_WORLD
#define N 1000000
#define iters 1000

int main(int argc, char** argv)
{
  int ierr=0;
  ierr=MPI_Init(&argc,&argv);

  int np, iam;

  ierr=MPI_Comm_size(MCW, &np);
  ierr=MPI_Comm_rank(MCW, &iam);

  if (np !=2)
    MPI_Abort(MCW,-1);

  double buf[N];

  for (int i=0; i<N; ++i)
    buf[i]=(double)(i % 256);

  MPI_Status status;

  for (int iter=0; iter < iters; ++iter)
    {
      
      if (iam==0)
	MPI_Send(&buf[0],N,MPI_DOUBLE,1,0,MCW);
      else
	MPI_Recv(&buf[0],N,MPI_DOUBLE,0,0,MCW,&status);
    }

  MPI_Finalize();

  return 0;
}
