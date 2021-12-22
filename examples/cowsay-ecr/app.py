# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Copyright 2020 Amazon.com, Inc. or its affiliates. All Rights Reserved.
"""

import os
import sys

from awslambdaric import bootstrap
import faassupervisor.supervisor as supervisor

def main(args):
    app_root = os.getcwd()
    handler = args[1]
    lambda_runtime_api_addr = os.environ["AWS_LAMBDA_RUNTIME_API"]

    bootstrap.run(app_root, handler, lambda_runtime_api_addr)


if __name__ == "__main__":
    main(sys.argv)