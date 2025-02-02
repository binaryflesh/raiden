from unittest.mock import Mock, patch

import pytest
import requests
from eth_utils import is_checksum_address, to_checksum_address

from raiden.constants import RoutingMode
from raiden.network.pathfinding import configure_pfs, get_random_service
from raiden.tests.utils.factories import HOP1
from raiden.tests.utils.smartcontracts import deploy_service_registry_and_set_urls
from raiden.utils import privatekey_to_address


def test_service_registry_random_pfs(
        service_registry_address,
        private_keys,
        web3,
        contract_manager,
):
    addresses = [
        to_checksum_address(privatekey_to_address(key))
        for key in private_keys
    ]
    c1_service_proxy, urls = deploy_service_registry_and_set_urls(
        private_keys=private_keys,
        web3=web3,
        contract_manager=contract_manager,
        service_registry_address=service_registry_address,
    )
    assert c1_service_proxy.service_count('latest') == 3

    # Test that getting the url for each service address works
    for idx, address in enumerate(addresses):
        assert c1_service_proxy.get_service_url('latest', address) == urls[idx]
    # Test that getting the url for a non-existing service address returns None
    assert c1_service_proxy.get_service_url('latest', to_checksum_address(HOP1)) is None

    # Test that get_service_address by index works
    for idx, address in enumerate(addresses):
        assert c1_service_proxy.get_service_address('latest', idx) == address

    # Test that getting the address for an index out of bounds returns None
    assert not c1_service_proxy.get_service_address('latest', 9999)

    # Test that getting a random service from the proxy works
    assert get_random_service(c1_service_proxy, 'latest') in zip(urls, addresses)


def test_configure_pfs(
        service_registry_address,
        private_keys,
        web3,
        contract_manager,
):
    service_proxy, urls = deploy_service_registry_and_set_urls(
        private_keys=private_keys,
        web3=web3,
        contract_manager=contract_manager,
        service_registry_address=service_registry_address,
    )
    json_data = {
        'price_info': 0,
        'network_info': {
            'chain_id': 1,
            'registry_address': '0xB9633dd9a9a71F22C933bF121d7a22008f66B908',
        },
        'message': 'This is your favorite pathfinding service',
        'operator': 'John Doe',
        'version': '0.0.1',
    }

    response = Mock()
    response.configure_mock(status_code=200)
    response.json = Mock(return_value=json_data)

    # With basic routing configure pfs should return None
    config = configure_pfs(
        pfs_address=None,
        pfs_eth_address=None,
        routing_mode=RoutingMode.BASIC,
        service_registry=service_proxy,
    )
    assert config is None

    # Asking for auto address
    with patch.object(requests, 'get', return_value=response):
        config = configure_pfs(
            pfs_address='auto',
            pfs_eth_address=None,
            routing_mode=RoutingMode.PFS,
            service_registry=service_proxy,
        )
    assert config.url in urls
    assert is_checksum_address(config.eth_address)

    # Configuring a given address
    given_address = 'http://ourgivenaddress'
    given_eth_address = '0x22222222222222222222'
    with patch.object(requests, 'get', return_value=response):
        config = configure_pfs(
            pfs_address=given_address,
            pfs_eth_address=given_eth_address,
            routing_mode=RoutingMode.PFS,
            service_registry=service_proxy,
        )
    assert config.url == given_address
    assert config.eth_address == given_eth_address
    assert config.fee == json_data['price_info']

    # Bad address, should exit the program
    response = Mock()
    response.configure_mock(status_code=400)
    bad_address = 'http://badaddress'
    pfs_eth_address = '0x22222222222222222222'
    with pytest.raises(SystemExit):
        with patch.object(requests, 'get', side_effect=requests.RequestException()):
            # Configuring a given address
            config = configure_pfs(
                pfs_address=bad_address,
                pfs_eth_address=pfs_eth_address,
                routing_mode=RoutingMode.PFS,
                service_registry=service_proxy,
            )
