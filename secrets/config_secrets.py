# coding: latin-1
###############################################################################
# Copyright (c) 2023 European Commission
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
###############################################################################

"""
Configuration of service secrets
"""

import os

flask_secret_key = os.getenv("FLASK_SECRET_KEY", "secret_here")
eidasnode_lightToken_secret = os.getenv("EIDASNODE_LIGHTTOKEN_SECRET", "secret_here")
revocation_api_key = os.getenv("REVOCATION_API_KEY", None)
hmac_secret = os.getenv("HMAC_SECRET", "")  # Default empty, meaning no HMAC check in JWT request

