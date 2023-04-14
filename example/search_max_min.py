# Copyright 2022 SpinQ Technology Co., Ltd.
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
from spinqit.algorithm import QSearching

dataset = [2, 3, 1, 4, 5, 6, 7, 15]
seed = 330
max_searcher = QSearching(seed=seed)
max_idx = max_searcher.search(dataset, show=False)
min_searcher = QSearching(find='min', seed=seed)
min_idx = min_searcher.search(dataset, show=False)
print(max_idx, min_idx)