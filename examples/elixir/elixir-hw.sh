#! /bin/sh

# SCAR - Serverless Container-aware ARchitectures
# Copyright (C) GRyCAP - I3M - UPV 
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


#Elixir example from: https://github.com/philnash/elixir-examples/tree/master/hello-world

cd /tmp

export LANG=en_US.UTF-8
cat << EOF > hello-world.exs
IO.puts "Hello World from Elixir code!"
EOF

elixir hello-world.exs