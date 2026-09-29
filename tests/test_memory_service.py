def test_ensure_customer_bank_creates_directives_and_mental_model(memory, fake_client):
    memory.ensure_customer_bank("cust_1", "Test Customer")
    bank = fake_client.banks["customer::cust_1"]
    assert len(bank.directives) == 3
    assert any(mm["name"] == "Customer Profile" for mm in bank.mental_models.values())


def test_ensure_shared_bank_creates_known_issues_mental_model(memory, fake_client):
    memory.ensure_shared_bank()
    bank = fake_client.banks["product::known-issues"]
    assert any(mm["name"] == "Known Issues Digest" for mm in bank.mental_models.values())


def test_retain_and_recall_known_issues(memory):
    memory.ensure_shared_bank()
    memory.client.retain(
        bank_id="product::known-issues",
        content="Recurring issue in module 'sync-engine'. Root cause: sleep-wake-stall.",
        tags=["known-issue", "module:sync-engine"],
    )
    results = memory.recall_known_issues("my sync stalls after sleep")
    assert len(results) == 1
    assert "sleep-wake-stall" in results[0].text


def test_reflect_reply_returns_structured_outcome(memory):
    memory.ensure_customer_bank("cust_2", "Marcus")
    memory.retain_customer_message("cust_2", "tick_1", "My sync is stuck again over VPN")
    outcome = memory.reflect_reply("cust_2", "My sync is stuck again over VPN", [])
    assert outcome.reply
    assert outcome.sentiment in ("neutral", "frustrated", "positive", "angry")
    assert outcome.based_on_directive_count == 3  # the 3 support directives


def test_seed_resolved_ticket_writes_customer_and_shared_bank(memory, fake_client):
    memory.ensure_shared_bank()
    memory.ensure_customer_bank("cust_3", "Dana")
    memory.seed_resolved_ticket(
        customer_id="cust_3", ticket_id="tick_9", timestamp="2026-01-01T00:00:00Z",
        customer_message="Sync stalls after sleep", resolution_summary="Reconnected session.",
        sentiment="neutral", resolved=True, root_cause_tag="sleep-wake-stall",
        is_known_issue=True, module="sync-engine",
    )
    customer_bank = fake_client.banks["customer::cust_3"]
    shared_bank = fake_client.banks["product::known-issues"]
    assert len(customer_bank.memories) == 2  # message + resolution
    assert len(shared_bank.memories) == 1
    assert "sleep-wake-stall" in shared_bank.memories[0]["content"]


def test_refresh_mental_models_populates_content(memory, fake_client):
    memory.ensure_customer_bank("cust_4", "Priya")
    memory.retain_customer_message("cust_4", "tick_x", "Sync is slow on first setup")
    memory.refresh_customer_profile("cust_4")
    content = memory.customer_profile("cust_4")
    assert content is not None
    assert "Customer Profile digest" in content
