#include <stdio.h>
void twiddle1(long *xp,long *yp)
{
	*xp += *yp;
	*xp += *yp;
}
void twiddle2(long *xp,long *yp)
{
	*xp += 2* *yp;
}
int main()
{
   long *xp,*yp;
   long x = 1;
   xp = &x;
   yp = xp;
   twiddle2(xp,yp);
   printf("%ld",*xp);
}

