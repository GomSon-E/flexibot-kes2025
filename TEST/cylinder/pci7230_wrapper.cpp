#include <windows.h>
#include "Dask64.h"

// 전역 변수로 상태 관리
static I16 g_card = -1;
static U32 g_output_state = 0x00000000;

extern "C" {
    // 카드 초기화
    __declspec(dllexport) I16 PCI7230_Init(int card_number) {
        g_card = Register_Card(PCI_7230, card_number);
        g_output_state = 0x00000000;
        return g_card;
    }
    
    // 카드 해제
    __declspec(dllexport) I16 PCI7230_Release() {
        if (g_card >= 0) {
            I16 result = Release_Card(g_card);
            g_card = -1;
            return result;
        }
        return -1;
    }
    
    // 채널 제어 (0-15)
    __declspec(dllexport) I16 PCI7230_SetChannel(int channel, int state) {
        if (g_card < 0) return -1;
        if (channel < 0 || channel > 15) return -1;
        
        if (state) {
            g_output_state |= (1 << channel);
        } else {
            g_output_state &= ~(1 << channel);
        }
        
        return DO_WritePort(g_card, 0, (U32)g_output_state);
    }
    
    // 채널 읽기 (0-15)
    __declspec(dllexport) I16 PCI7230_ReadChannel(int channel, int* state) {
        if (g_card < 0) return -1;
        if (channel < 0 || channel > 15) return -1;
        
        U32 value;
        I16 result = DI_ReadPort(g_card, 0, &value);
        
        if (result >= 0) {
            *state = (value >> channel) & 1;
        }
        
        return result;
    }
    
    // 전체 포트 쓰기
    __declspec(dllexport) I16 PCI7230_WritePort(U32 value) {
        if (g_card < 0) return -1;
        g_output_state = value;
        return DO_WritePort(g_card, 0, value);
    }
    
    // 전체 포트 읽기
    __declspec(dllexport) I16 PCI7230_ReadPort(U32* value) {
        if (g_card < 0) return -1;
        return DI_ReadPort(g_card, 0, value);
    }
}