import pytest

from raiden.tests.utils.detect_failure import raise_on_failure
from raiden.tests.utils.events import search_for_item
from raiden.tests.utils.network import CHAIN
from raiden.tests.utils.transfer import transfer
from raiden.transfer.mediated_transfer.events import (
    EventUnlockClaimSuccess,
    EventUnlockSuccess,
    SendSecretRequest,
    SendSecretReveal,
)
from raiden.utils import wait_until


@pytest.mark.parametrize('channels_per_node', [CHAIN])
@pytest.mark.parametrize('number_of_nodes', [3])
def test_mediated_transfer_events(raiden_network, number_of_nodes, token_addresses, network_wait):
    raise_on_failure(
        raiden_network,
        run_test_mediated_transfer_events,
        raiden_network=raiden_network,
        number_of_nodes=number_of_nodes,
        token_addresses=token_addresses,
        network_wait=network_wait,
    )


def run_test_mediated_transfer_events(
        raiden_network,
        number_of_nodes,
        token_addresses,
        network_wait,
):
    app0, app1, app2 = raiden_network
    token_address = token_addresses[0]

    amount = 10
    transfer(
        initiator_app=app0,
        target_app=app2,
        token_address=token_address,
        amount=amount,
        identifier=1,
        timeout=network_wait * number_of_nodes,
    )

    def test_initiator_events():
        initiator_events = app0.raiden.wal.storage.get_events()
        return (
            search_for_item(initiator_events, SendSecretReveal, {}) and
            search_for_item(initiator_events, EventUnlockSuccess, {})
        )

    assert wait_until(test_initiator_events, network_wait)

    def test_mediator_events():
        mediator_events = app1.raiden.wal.storage.get_events()
        return (
            search_for_item(mediator_events, EventUnlockSuccess, {}) and
            search_for_item(mediator_events, EventUnlockClaimSuccess, {})
        )

    assert wait_until(test_mediator_events, network_wait)

    def test_target_events():
        target_events = app2.raiden.wal.storage.get_events()
        return (
            search_for_item(target_events, SendSecretRequest, {}) and
            search_for_item(target_events, SendSecretReveal, {}) and
            search_for_item(target_events, EventUnlockClaimSuccess, {})
        )

    assert wait_until(test_target_events, network_wait)
