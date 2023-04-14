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

#ifndef SPINQINTERFACE_HH
#define SPINQINTERFACE_HH

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

/**
 * @brief connect_to_server: The interface must be called one time before calling other interface.
 * @param address: The ip address of server.
 * @param port: The port of server.
 * @return The section ID of websocket, -1: error
 */
SPINQ_API void connect_to_server(const char* address, const unsigned short port);

/**
 * @brief set_on_opened_callback: Set the callback function of opened(connect to server successfully).
 */
SPINQ_API void set_on_opened_callback(void (*func)(void));

/**
 * @brief set_on_failed_callback: Set the callback funcation of failed(connect to server failed).
 */
SPINQ_API void set_on_failed_callback(void (*func)(void));

/**
 * @brief set_on_closed_callback: Set the callback funcation of closed(the client has been disconnected from server).
 */
SPINQ_API void set_on_closed_callback(void (*func)(void));

/**
 * @brief disconnect_from_server: Disconnect from server.
 */
SPINQ_API void disconnect_from_server();

/**
 * @brief push_task_request: Push a task to server.
 * @param name: The name of task.
 * @param description: The description of task.
 * @param gates: The quantum circuit of task.
 * @param qubits：1: one-quantum task, 2: two-quantum task.
 * @return The ID of the task, return -1 if push message server failed.
 */
SPINQ_API unsigned long long push_task_request(const char* name,
                                               const char* description,
                                               const char* gates,
                                               const int qubits);

/**
 * @brief get_task_state: Get the task state
 * @param task_id：task id
 * @return 1: task finished, 0: task running
 */
SPINQ_API int get_task_state(const char* task_id);

/**
 * @brief get_task_result: Get the task result
 * @param task_id: task id
 * @return task result, when the result is not ready, return NULL
 */
SPINQ_API const char* get_task_result(const char* task_id);

/**
 * @brief set_push_task_response_callback: set push task response callback
 */
SPINQ_API void set_push_task_response_callback(void (*func)(const char*));

/**
 * @brief set_task_finished_post_callback: set task finished post callback
 */
SPINQ_API void set_task_finished_post_callback(void (*func)(const char*));

/**
 * @brief emit_pulse_request: emit pulse request
 * @param json: pulse parameters
 * @param length: pulse parameter length
 * @param pps_flag: whether pps before sending the pulse
 * @param sample_frequence: sample frequence
 * @param sample_points: sample points
 * @param fft_points: FFT data points
 * @param fft_from: FFT data start index
 * @param fft_to: FFT data end index
 * @param channel: channel
 * @return 0 means successful
 */
SPINQ_API unsigned long long emit_pulse_request(const char* json,
                                                const int length,
                                                const int pps_flag,
                                                const int sample_frequence,
                                                const int sample_points,
                                                const int fft_points,
                                                const int fft_from,
                                                const int fft_to,
                                                const int channel);

/**
 * @brief get_sending_pulse_state: get sending pulse state
 * @return pulse sending state
 */
SPINQ_API int get_emit_pulse_state(const char* pulse_id);

/**
 * @brief get_sending_pluse_result：get sending pulse result
 * @return pulse sending result, when the result is not ready, return NULL
 */
SPINQ_API const char* get_emit_pluse_result(const char *pluse_id);

/**
 * @brief set_emit_pluse_response_callback: set emit pulse response callback
 */
SPINQ_API void set_emit_pluse_response_callback(void (*func)(const char*));

/**
 * @brief set_emit_pulse_finished_post_callback: set emit pulse finished post callback
 */
SPINQ_API void set_emit_pulse_finished_post_callback(void (*func)(const char*));

#ifdef __cplusplus
}
#endif  // __cplusplus

#endif  // SPINQINTERFACE_HH
