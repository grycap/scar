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


#Erlang example from: http://www.thegeekstuff.com/2010/05/erlang-hello-world-example/

cd /tmp

cat << EOF > helloworld.erl
% hello world program
-module(helloworld).
-export([start/0]).

start() ->
    io:fwrite("Hello, world from Erlang code!\n").
EOF

erlc helloworld.erl

erl -noshell -s helloworld start -s init stop