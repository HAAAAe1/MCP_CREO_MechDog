// Only the registered loader links Toolkit. Payloads call this explicit host API,
// so no unregistered Toolkit DLL runtime or private initialization is involved.
#pragma once
#include <ProToolkitDll.h>
#include <ProUICmd.h>
#include <ProMdl.h>
#include <ProModelitem.h>
#include <ProSelection.h>
#include <ProArray.h>

struct MechDogCallbackApi {
    int abi;
    size_t size;
    decltype(&ProArraySizeGet) array_size;
    decltype(&ProArrayAlloc) array_alloc;
    decltype(&ProArgumentProarrayFree) arguments_free;
    decltype(&ProValuedataWstringSet) wstring_set;
    decltype(&ProMdlCurrentGet) current_model;
    decltype(&ProMdlMdlnameGet) model_name;
    decltype(&ProModelitemInit) model_item;
    decltype(&ProSelectionAlloc) selection_alloc;
    decltype(&ProSelectExternalselectionRecord) selection_record;
    decltype(&ProSelectionFree) selection_free;
    decltype(&ProCmdActionAdd) command_add;
};
