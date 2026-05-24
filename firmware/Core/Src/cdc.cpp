/*
 * cdc_driver.cpp
 *
 *  Created on: Feb 10, 2026
 *      Author: habib
 */

#include "cdc_driver.h"
#include "usbd_cdc_if.h"
#include <cstring>
#include <cstdio>
#include <cstdarg>

CdcDriver *g_usbCdcDriver = nullptr;

/* Implement the Bridge Function (The C file calls this) */ // chat added this
extern "C" void CDC_Rx_Callback(uint8_t *buf, uint32_t len)
{
    if (g_usbCdcDriver != nullptr)
    {
        g_usbCdcDriver->onDataReceived(buf, len);
    }
}

CdcDriver::CdcDriver(uint32_t timeout_ms)
    : m_timeout_ms(timeout_ms), rx_len(0), data_received(false)
{
    g_usbCdcDriver = this;
}

void CdcDriver::init()
{
}

bool CdcDriver::sendMessage(const Message *msg)
{
    uint8_t buffer[67];
    size_t index = 0;

    // Pack message
    buffer[index++] = START_BYTE;
    buffer[index++] = msg->type;
    buffer[index++] = msg->size;
    memcpy(&buffer[index], &msg->value, msg->size);
    index += msg->size;

    uint8_t result = CDC_Transmit_FS(buffer, index);

    return (result == USBD_OK);
}

void CdcDriver::print(const char *format, ...)
{
    char buffer[128];       // char array to hold the final formatted string
    va_list args;           // acts as container for all extra arguments passed after format
    va_start(args, format); // initalize the container
    int len = vsnprintf(buffer, sizeof(buffer), format, args);
    va_end(args); // required after the va_start to clean up the va_list

    uint32_t start_time = HAL_GetTick();
    if (len > 0)
    {
        while (CDC_Transmit_FS((uint8_t *)buffer, len) == USBD_BUSY)
        {
            if (HAL_GetTick() - start_time > 10)
                break; // give up after 10 ms if the bus is busy
        }
    }
}

bool CdcDriver::receiveMessage(Message *msg)
{

    if (!data_received)
    {
        return false; // No data, return immediately
    }

    // uint32_t start_time = HAL_GetTick();

    // while (!data_received) {
    //     if ((HAL_GetTick() - start_time) > m_timeout_ms) {
    //         return false; // timeout
    //     }
    // }

    uint16_t start_index = 0;
    bool found_start = false;

    // Search for START_BYTE
    for (uint16_t i = 0; i < rx_len; i++)
    {
        if (m_rx_buffer[i] == START_BYTE)
        {
            start_index = i;
            found_start = true;
            break;
        }
    }

    if (!found_start || (rx_len - start_index) < 3)
    {
        data_received = false;
        return false;
    }

    // Parse
    uint16_t idx = start_index + 1;
    msg->type = static_cast<MessageType>(m_rx_buffer[idx++]);
    msg->size = m_rx_buffer[idx++];

    if (msg->size > 64 || (idx + msg->size) > rx_len)
    {
        data_received = false;
        return false;
    }
    memcpy(&msg->value, &m_rx_buffer[idx], msg->size);

    data_received = false;
    return true;
}

bool CdcDriver::available() const
{
    return data_received;
}

void CdcDriver::onDataReceived(uint8_t *buf, uint32_t len)
{
    if (len > sizeof(m_rx_buffer))
    {
        len = sizeof(m_rx_buffer);
    }

    memcpy(m_rx_buffer, buf, len);
    rx_len = len;
    data_received = true;
}