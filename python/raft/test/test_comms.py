# Copyright (c) 2019, NVIDIA CORPORATION.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

import pytest

import random

import raft

from dask.distributed import Client, wait

from raft.dask.common import CommsContext, worker_state
from raft.dask.common import perform_test_comms_send_recv
from raft.dask.common import perform_test_comms_allreduce

pytestmark = pytest.mark.mg


def test_comms_init_no_p2p(cluster):

    client = Client(cluster)

    try:
        cb = CommsContext(comms_p2p=False)
        cb.init()

        assert cb.nccl_initialized is True
        assert cb.ucx_initialized is False

    finally:

        cb.destroy()
        client.close()


def func_test_allreduce(sessionId, r):
    handle = worker_state(sessionId)["handle"]
    return perform_test_comms_allreduce(handle)


def func_test_send_recv(sessionId, n_trials, r):
    handle = worker_state(sessionId)["handle"]
    return perform_test_comms_send_recv(handle, n_trials)



@pytest.mark.nccl
def test_allreduce(cluster):

    client = Client(cluster)

    try:
        cb = CommsContext()
        cb.init()

        dfs = [client.submit(func_test_allreduce, cb.sessionId,
                             random.random(), workers=[w])
               for w in cb.worker_addresses]
        wait(dfs, timeout=5)

        assert all([x.result() for x in dfs])

    finally:
        cb.destroy()
        client.close()


@pytest.mark.ucx
@pytest.mark.parametrize("n_trials", [1, 5])
def test_send_recv(n_trials, ucx_cluster):

    client = Client(ucx_cluster)

    try:

        cb = CommsContext(comms_p2p=True, verbose=True)
        cb.init()

        dfs = [client.submit(func_test_send_recv,
                             cb.sessionId,
                             n_trials,
                             random.random(),
                             workers=[w])
               for w in cb.worker_addresses]

        wait(dfs, timeout=5)

        assert(list(map(lambda x: x.result(), dfs)))

    finally:
        cb.destroy()
        client.close()
