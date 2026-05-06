# Search and listing indexes (PostgreSQL)

Verified against migrations:

- **`smart_blog_item_search_vector_gin`** — GIN index on `Item.search_vector`, created in migration `0017_trigger_search_vector` / `0016_item_search_vector_fts`. Used for full-text search (`build_search_filter` + `tsvector`).
- **Triggers** keep `search_vector` in sync on insert/update and tag M2M changes (`0019_search_vector_tags_likes_count`).
- **Operational check:** for slow queries after large data growth, run `EXPLAIN (ANALYZE, BUFFERS)` on the search queryset and on `items_list`-style filters (`is_published`, `published_date`, exists on likes/bookmarks).

No new migration was required for this verification; indexes already exist in the schema.
