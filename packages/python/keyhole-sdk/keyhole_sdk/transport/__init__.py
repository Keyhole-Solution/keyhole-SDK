"""Transport abstractions — stable façade over HTTP internals.

Per §12.1: Internal transport helpers may evolve.
The public façade must remain stable.
"""

from keyhole_sdk.transport.http import HttpTransport

__all__ = ["HttpTransport"]
