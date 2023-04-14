/**
 * Copyright 2021 SpinQ Technology Co., Ltd.
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

#ifndef SPINQUSER_HH
#define SPINQUSER_HH

#ifdef BUILD_SPINQINTERFACE_DLL
    #define SPINQ_API __declspec(dllexport)
#else
    #ifdef _WIN64
        #define SPINQ_API __declspec(dllimport)
    #else
        #define SPINQ_API
    #endif
#endif

#ifdef __cplusplus
extern "C"
{
#endif

SPINQ_API int request_login(const char* account, const char* password);
SPINQ_API void set_login_response_callback(void (*func)(const char*));

SPINQ_API int request_pull_tasks(int page_index, const char* state);
SPINQ_API void set_pull_tasks_response_callback(void (*func)(const char*));

SPINQ_API int request_delete_task(const char* id);
SPINQ_API void set_delete_task_response_callback(void (*func)(const char*));

SPINQ_API int request_get_number_of_task_records(const char* state);
SPINQ_API void set_get_number_of_task_records_response_callback(void (*func)(const char*));

SPINQ_API void set_task_started_post_callback(void (*func)(const char*));

SPINQ_API int request_get_task_queue_info();
SPINQ_API void set_get_task_queue_info_response_callback(void (*func)(const char*));

#ifdef __cplusplus
}
#endif  // __cplusplus

#endif  // SPINQUSER_HH
