/* Local Bionic instruction-cache maintenance for the experimental MonoMod probe. */
void mm_clear_cache(void *start, void *end) {
    __builtin___clear_cache((char *)start, (char *)end);
}
