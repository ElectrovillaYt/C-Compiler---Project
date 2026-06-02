#include <stdio.h>
#define MAX 10

int main()
{
    int arr[] = {1, 2, 3, 4, 5, 6, 7, 8, 9, 10};
    printf("Sample Loop Code!\n");

    for (int i = 1; i < MAX + 1; i++)
    {
        printf("Running Loop for %d iteration!\n", i);
    }

    return 0;
}