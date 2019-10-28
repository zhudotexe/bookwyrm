def ensure_collections(mdb):
    # rewards
    mdb.rewards.delegate.create_index("message_id", unique=True)
    mdb.rewards.delegate.create_index("time_last_edited")
