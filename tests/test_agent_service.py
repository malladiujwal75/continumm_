from app.agent_service import AgentService, NoMemoryStrategy, WithMemoryStrategy
from app.llm_baseline import BaselineLLM


def test_no_memory_strategy_makes_no_retain_calls(fake_client, test_settings):
    baseline = BaselineLLM(test_settings)
    strategy = NoMemoryStrategy(baseline)
    reply = strategy.respond("cust_1", "tick_1", "Help, my sync is broken")
    assert reply.memory_mode == "off"
    assert fake_client.banks == {}  # nothing retained anywhere


def test_with_memory_strategy_writes_back_resolution(memory, fake_client):
    memory.ensure_customer_bank("cust_2", "Marcus")
    strategy = WithMemoryStrategy(memory)
    reply = strategy.respond("cust_2", "tick_2", "My sync is stuck over VPN again")
    assert reply.memory_mode == "on"
    bank = fake_client.banks["customer::cust_2"]
    # customer message + resolution write-back, at minimum
    assert len(bank.memories) >= 2
    assert "memories_used" in reply.meta


def test_with_memory_strategy_flags_known_issue_into_shared_bank(memory, fake_client):
    memory.ensure_shared_bank()
    memory.ensure_customer_bank("cust_3", "Dana")
    # Seed enough prior VPN/sync memories so the fake's heuristic marks this a known issue.
    for i in range(3):
        memory.retain_customer_message("cust_3", f"tick_hist_{i}", "sync vpn issue again")
    strategy = WithMemoryStrategy(memory)
    reply = strategy.respond("cust_3", "tick_live", "my sync vpn is stuck again")
    assert reply.meta["is_known_issue"] is True
    shared_bank = fake_client.banks["product::known-issues"]
    assert len(shared_bank.memories) >= 1


def test_agent_service_handle_message_persists_transcript(memory, fake_client, tickets_repo, customers_repo, test_settings):
    from app.llm_baseline import BaselineLLM
    customers_repo.create(name="Marcus", customer_id="cust_4")
    memory.ensure_customer_bank("cust_4", "Marcus")
    ticket = tickets_repo.create(customer_id="cust_4", subject="Sync issue")

    agent = AgentService(tickets_repo, memory, BaselineLLM(test_settings))
    msg = agent.handle_message("cust_4", ticket.id, "My sync is stuck", memory_mode="on")

    assert msg.role == "agent"
    transcript = tickets_repo.list_messages(ticket.id)
    assert len(transcript) == 2  # customer + agent
    assert transcript[0].role == "customer"
    assert transcript[1].role == "agent"


def test_agent_service_off_mode_uses_no_memory_strategy(memory, fake_client, tickets_repo, customers_repo, test_settings):
    from app.llm_baseline import BaselineLLM
    customers_repo.create(name="Priya", customer_id="cust_5")
    memory.ensure_customer_bank("cust_5", "Priya")
    ticket = tickets_repo.create(customer_id="cust_5", subject="Slow sync")

    agent = AgentService(tickets_repo, memory, BaselineLLM(test_settings))
    msg = agent.handle_message("cust_5", ticket.id, "Why is sync slow", memory_mode="off")

    assert msg.memory_mode == "off"
    bank = fake_client.banks.get("customer::cust_5")
    # bank exists (created by ensure_customer_bank) but got no new memories from the off-mode message
    assert bank is not None
    assert len(bank.memories) == 0
