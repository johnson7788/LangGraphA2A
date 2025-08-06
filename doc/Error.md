# 报错Unknown field for Part: thought， 需要修改langchain的版本和google版本
pip install langchain-google-genai==2.1.3
pip install google-ai-generativelanguage==0.6.17

# 报错，升级pip install --upgrade protobuf==6.31.1
Traceback (most recent call last):
  File "<frozen importlib._bootstrap>", line 1176, in _find_and_load
  File "<frozen importlib._bootstrap>", line 1147, in _find_and_load_unlocked
  File "<frozen importlib._bootstrap>", line 690, in _load_unlocked
  File "<frozen importlib._bootstrap_external>", line 940, in exec_module
  File "<frozen importlib._bootstrap>", line 241, in _call_with_frames_removed
  File "/Users/admin/miniforge3/envs/a2a/lib/python3.11/site-packages/a2a/server/apps/__init__.py", line 3, in <module>
    from a2a.server.apps.jsonrpc import (
  File "/Users/admin/miniforge3/envs/a2a/lib/python3.11/site-packages/a2a/server/apps/jsonrpc/__init__.py", line 3, in <module>
    from a2a.server.apps.jsonrpc.fastapi_app import A2AFastAPIApplication
  File "/Users/admin/miniforge3/envs/a2a/lib/python3.11/site-packages/a2a/server/apps/jsonrpc/fastapi_app.py", line 7, in <module>
    from a2a.server.apps.jsonrpc.jsonrpc_app import (
  File "/Users/admin/miniforge3/envs/a2a/lib/python3.11/site-packages/a2a/server/apps/jsonrpc/jsonrpc_app.py", line 21, in <module>
    from a2a.server.request_handlers.jsonrpc_handler import JSONRPCHandler
  File "/Users/admin/miniforge3/envs/a2a/lib/python3.11/site-packages/a2a/server/request_handlers/__init__.py", line 6, in <module>
    from a2a.server.request_handlers.grpc_handler import GrpcHandler
  File "/Users/admin/miniforge3/envs/a2a/lib/python3.11/site-packages/a2a/server/request_handlers/grpc_handler.py", line 10, in <module>
    import a2a.grpc.a2a_pb2_grpc as a2a_grpc
  File "/Users/admin/miniforge3/envs/a2a/lib/python3.11/site-packages/a2a/grpc/a2a_pb2_grpc.py", line 5, in <module>
    from . import a2a_pb2 as a2a__pb2
  File "/Users/admin/miniforge3/envs/a2a/lib/python3.11/site-packages/a2a/grpc/a2a_pb2.py", line 12, in <module>
    _runtime_version.ValidateProtobufRuntimeVersion(
  File "/Users/admin/miniforge3/envs/a2a/lib/python3.11/site-packages/google/protobuf/runtime_version.py", line 106, in ValidateProtobufRuntimeVersion
    _ReportVersionError(
  File "/Users/admin/miniforge3/envs/a2a/lib/python3.11/site-packages/google/protobuf/runtime_version.py", line 50, in _ReportVersionError
    raise VersionError(msg)
google.protobuf.runtime_version.VersionError: Detected mismatched Protobuf Gencode/Runtime major versions when loading a2a.proto: gencode 6.31.1 runtime 5.29.5. Same major version is required. See Protobuf version guarantees at https://protobuf.dev/support/cross-version-runtime-guarantee.
python-BaseException


# 报错
Traceback (most recent call last):
  File "/Users/admin/git/LangGraphA2A/backend/app/a2a_client.py", line 190, in <module>
    asyncio.run(main())
  File "/Users/admin/miniforge3/envs/a2a/lib/python3.11/asyncio/runners.py", line 190, in run
    return runner.run(main)
           ^^^^^^^^^^^^^^^^
  File "/Users/admin/miniforge3/envs/a2a/lib/python3.11/asyncio/runners.py", line 118, in run
    return self._loop.run_until_complete(task)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/Users/admin/miniforge3/envs/a2a/lib/python3.11/asyncio/base_events.py", line 654, in run_until_complete
    return future.result()
           ^^^^^^^^^^^^^^^
  File "/Users/admin/git/LangGraphA2A/backend/app/a2a_client.py", line 170, in main
    second_response = await client.send_message(second_request)
                      ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/Users/admin/miniforge3/envs/a2a/lib/python3.11/site-packages/a2a/utils/telemetry.py", line 161, in async_wrapper
    result = await func(*args, **kwargs)
             ^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/Users/admin/miniforge3/envs/a2a/lib/python3.11/site-packages/a2a/client/client.py", line 213, in send_message
    **await self._send_request(
      ^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/Users/admin/miniforge3/envs/a2a/lib/python3.11/site-packages/a2a/utils/telemetry.py", line 161, in async_wrapper
    result = await func(*args, **kwargs)
             ^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/Users/admin/miniforge3/envs/a2a/lib/python3.11/site-packages/a2a/client/client.py", line 303, in _send_request
    raise A2AClientHTTPError(
a2a.client.errors.A2AClientHTTPError: HTTP Error 503: Network communication error: 
