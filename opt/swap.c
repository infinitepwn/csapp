#include <stdio.h>
void swap(int* xp,int*yp){
	*xp = *xp + *yp;
	*yp = *xp - *yp;
	*xp = *xp - *yp;
}
int main(){
	int x = 1;
	int y = 2;
	printf("%d%d\n",x,y);
	int* xp = &x;
	int* yp = &y;
	swap(xp,yp);
	printf("after swap\n");
	printf("%d%d\n",x,y);
	printf("if *xp = *yp\n");
	//now x = 2,y=1
	xp = &x;
	yp = &x;
	swap(xp,yp);
	printf("%d%d",*xp,*yp);
}
