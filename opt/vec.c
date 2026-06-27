#include <stdlib.h>
#include <stdio.h>
#include "combine.h"
#include <time.h>
/* $begin vec */
/* Create vector of specified length */
vec_ptr new_vec(long len)
{
    /* Allocate header structure */
    vec_ptr result = (vec_ptr) malloc(sizeof(vec_rec));
    data_t *data = NULL;
    if (!result)
        return NULL;  /* Couldn't allocate storage */
    result->len = len;
/* $end vec */
    /* We don't show this in the book */
    result->allocated_len = len;
/* $begin vec */
    /* Allocate array */
    if (len > 0) {
        data = (data_t *)calloc(len, sizeof(data_t));
	if (!data) {
	    free((void *) result);
 	    return NULL; /* Couldn't allocate storage */
	}
    }
    /* data will either be NULL or allocated array */
    result->data = data;
    return result;
}

/* Free storage used by vector */
void free_vec(vec_ptr v) {
    if (v->data)
	free(v->data);
    free(v);
}

/*
 * Retrieve vector element and store at dest.
 * Return 0 (out of bounds) or 1 (successful)
 */
int get_vec_element(vec_ptr v, long index, data_t *dest)
{
    if (index < 0 || index >= v->len)
	return 0;
    *dest = v->data[index];
    return 1;
}

/* Return length of vector */
long vec_length(vec_ptr v)
{
    return v->len;
}
/* $end vec */


/* $begin get_vec_start */
data_t *get_vec_start(vec_ptr v)
{
    return v->data;
}
/* $end get_vec_start */


/*
 * Set vector element.
 * Return 0 (out of bounds) or 1 (successful)
 */
int set_vec_element(vec_ptr v, long index, data_t val)
{
    if (index < 0 || index >= v->len)
	return 0;
    v->data[index] = val;
    return 1;
}


/* Set vector length.  If >= allocated length, will reallocate */
void set_vec_length(vec_ptr v, long newlen)
{
    if (newlen > v->allocated_len) {
	free(v->data);
	v->data = (data_t *) calloc(newlen, sizeof(data_t));
	v->allocated_len = newlen;
    }
    v->len = newlen;
}
void combine1(vec_ptr v, data_t *dest)
{
    long i;
    *dest = IDENT;
    for (i = 0; i < vec_length(v); i++){
        data_t val;
        get_vec_element(v, i, &val);
        *dest = *dest OP val; 
    }
}
void combine2(vec_ptr v, data_t *dest)
{
    long i;
    long length = vec_length(v);
    *dest = IDENT;
    for (i = 0; i < length; i++){
        data_t val;
        get_vec_element(v, i, &val);
        *dest = *dest OP val; 
    }
}
void combine3(vec_ptr v, data_t *dest)
{
    long i;
    long length = vec_length(v);
    data_t *data = get_vec_start(v);
    *dest = IDENT;
    for (i = 0; i < length; i++){
        *dest = *dest OP data[i]; 
    }
}
#ifdef VEC_STANDALONE
int main()
{
    vec_ptr v = new_vec(1000000000);
    for (long i = 0; i < 1000000000; i++)
        set_vec_element(v, i, i);
    data_t result1, result2;
    clock_t start, end;
    start = clock();
    combine1(v, &result1);
    end = clock();
    printf("combine1 time: %f seconds\n", ((double)(end - start)) / CLOCKS_PER_SEC);
    start = clock();
    combine2(v, &result2);
    end = clock();
    printf("combine2 time: %f seconds\n", ((double)(end - start)) / CLOCKS_PER_SEC);    
    start = clock();
    combine3(v, &result1);
    end = clock();
    printf("combine3 time: %f seconds\n", ((double)(end - start)) / CLOCKS_PER_SEC);
    free_vec(v);
    return 0;
}
#endif
