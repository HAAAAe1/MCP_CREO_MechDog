// Synchronous selection callback. Only the immutable, private request next to
// this per-operation DLL copy can supply the model, command and native curves.
#define NOMINMAX
#include <windows.h>
#include <ProToolkitDll.h>
#include <ProUICmd.h>
#include <ProMdl.h>
#include <ProModelitem.h>
#include <ProSelection.h>
#include <fstream>
#include <string>
#include <vector>
#include "third_party/json.hpp"
using Json=nlohmann::json;
static std::wstring directory,expected_model;
static std::vector<int> curve_ids;
static Json outcome={{"selected",0},{"codes",Json::array()}};
static size_t section_index=0;
static bool safe_token(const std::string& value){
 if(value.empty()||value.size()>70)return false;
 for(char c:value)if(!((c>='a'&&c<='z')||(c>='A'&&c<='Z')||(c>='0'&&c<='9')||c=='_'))return false;return true;
}
static void persist(){std::ofstream f(directory+L"\\callback_result.json",std::ios::binary);f<<outcome.dump(2);}
static uiCmdAccessState access(uiCmdAccessMode){return ACCESS_AVAILABLE;}
static int select_section(uiCmdCmdId,uiCmdValue*,void*){
 ProSelection selected=nullptr;
 try{
  ProMdl model=nullptr;ProName name;ProError code=ProMdlCurrentGet(&model);
  if(!code)code=ProMdlNameGet(model,name);
  if(!code&&(_wcsicmp(name,expected_model.c_str())||section_index>=curve_ids.size()))code=PRO_TK_BAD_CONTEXT;
  ProModelitem item;if(!code)code=ProModelitemInit(model,curve_ids[section_index],PRO_CURVE,&item);
  if(!code)code=ProSelectionAlloc(nullptr,&item,&selected);
  if(!code)code=ProSelectExternalselectionRecord(selected,PRO_SELECT_OVERRIDE);
  if(selected){ProSelectionFree(&selected);selected=nullptr;}
  outcome["codes"].push_back(code);if(!code)section_index++;
  outcome["selected"]=section_index;persist();
 }catch(...){if(selected)ProSelectionFree(&selected);try{outcome["exception"]=true;persist();}catch(...){}}
 return 0;
}
extern "C" __declspec(dllexport) int user_initialize(int,char**,char*,char*,wchar_t errmsg[80]){
 try{
  wchar_t filename[MAX_PATH];HMODULE module=nullptr;
  if(!GetModuleHandleExW(GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS|GET_MODULE_HANDLE_EX_FLAG_UNCHANGED_REFCOUNT,(LPCWSTR)&user_initialize,&module)||!GetModuleFileNameW(module,filename,MAX_PATH))return PRO_TK_GENERAL_ERROR;
  directory=filename;directory=directory.substr(0,directory.find_last_of(L"\\"));
  std::ifstream input(directory+L"\\callback_request.json");Json request;input>>request;
  std::string name=request.at("model_name"),command=request.at("command");
  if(!safe_token(name)||name.size()>31||!safe_token(command))return PRO_TK_BAD_INPUTS;
  expected_model.assign(name.begin(),name.end());curve_ids=request.at("curve_ids").get<std::vector<int>>();
  if(curve_ids.size()<2||curve_ids.size()>20)return PRO_TK_BAD_INPUTS;
  for(int id:curve_ids)if(id<0)return PRO_TK_BAD_INPUTS;
  // Persist Creo's real identifier before exposing the command. A later worker
  // can locate this module after a loader prompt outlives the original process.
  ProName application_id;ProError identified=ProToolkitDllIdGet(nullptr,application_id);
  outcome["application_id_code"]=identified;
  if(!identified){std::wstring id=application_id;outcome["application_id"]=std::string(id.begin(),id.end());}
  persist();if(identified)return identified;
  uiCmdCmdId action;ProError code=ProCmdActionAdd(command.data(),select_section,uiProeAsynch,access,PRO_B_FALSE,PRO_B_FALSE,&action);
  outcome["initialize_code"]=code;persist();return code;
 }catch(...){wcscpy_s(errmsg,80,L"Invalid MechDog Blend callback request");return PRO_TK_BAD_INPUTS;}
}
extern "C" __declspec(dllexport) void user_terminate(){try{outcome["terminated"]=true;persist();}catch(...){}}
