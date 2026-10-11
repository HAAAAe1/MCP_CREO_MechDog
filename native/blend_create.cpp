// Creo 10 ordinary Blend: asynchronous orchestration with a small synchronous
// external-selection callback. All references are resolved before the dashboard.
#include <ProToolkitDll.h>
#include <ProSelbuffer.h>
#include <ProMenu.h>
static void generic_loft(const J& op){
 if(op.value("mode","add")!="add"||op.value("new_body",false))throw std::runtime_error("Direct Blend currently supports solid add into the default body only");
 J before=inspection(),curves=J::array();double previous_z=-HUGE_VAL;
 for(auto reference:op.at("sections")){
  int id=feature_id(reference);J meta;
  for(auto item:aliases)if(item.value("feature_id",-1)==id&&(item.value("op","")=="sketch"||item.value("op","")=="airfoil_sketch"))meta=item;
  if(meta.is_null()||!meta.contains("origin")||!meta.contains("normal"))throw std::runtime_error("Direct Blend requires MCP-owned independent XY sketches");
  V normal=vec(meta["normal"]),origin=vec(meta["origin"]),u=vec(meta["u_axis"]);
  if(fabs(normal[0])+fabs(normal[1])+fabs(normal[2]-1)+fabs(u[0]-1)+fabs(u[1])+fabs(u[2])+fabs(origin[0])+fabs(origin[1])>1e-7)throw std::runtime_error("Blend sections require XY frames with strictly increasing Z");
  ProFeature profile;CK(ProFeatureInit((ProSolid)board,id,&profile));ProFeattype type;CK(ProFeatureTypeGet(&profile,&type));if(type!=PRO_FEAT_CURVE)throw std::runtime_error("Blend section is not an independent sketch");
  ProSection actual=nullptr;CK(ProFeatureSectionCopy(&profile,0,&actual));ProMatrix location;ProError positioned=ProSectionLocationGet(actual,location);CK(ProSectionFree(&actual));check(positioned,"InspectActualBlendSectionPlane");
  if(fabs(location[2][0])+fabs(location[2][1])+fabs(fabs(location[2][2])-1)+fabs(location[3][0])+fabs(location[3][1])>1e-7||location[3][2]<=previous_z)throw std::runtime_error("Actual Blend section planes require XY frames with strictly increasing Z");
  previous_z=location[3][2];log("BLEND_ACTUAL_SECTION_PLANE feature=%d z=%.12f\n",id,previous_z);
  J items=J::array();CK(ProFeatureGeomitemVisit(&profile,PRO_CURVE,collect_geom_ids,nullptr,&items));bool found=false;
  for(auto item:items){ProCurve curve;CK(ProCurveInit((ProSolid)board,item["id"],&curve));ProEnttype kind;CK(ProCurveTypeGet(curve,&kind));if(kind!=PRO_ENT_CMP_CRV){curves.push_back(item["id"]);found=true;break;}}
  if(!found)throw std::runtime_error("Blend section has no selectable curve");
 }
 activate_blend_context();CK(ProSelbufferClear());
 std::string command="MechDogBlend_"+std::to_string(GetCurrentProcessId())+"_"+std::to_string(GetTickCount64());
 std::filesystem::path callback_dir=std::filesystem::path(generic_job)/command;
 std::filesystem::create_directory(callback_dir);wchar_t executable[MAX_PATH];GetModuleFileNameW(nullptr,executable,MAX_PATH);
 std::filesystem::path compiled=std::filesystem::path(executable).parent_path()/L"creo_blend_sync.dll";
 std::filesystem::copy_file(compiled,callback_dir/L"callback.dll",std::filesystem::copy_options::none);
 std::ofstream request(callback_dir/L"callback_request.json",std::ios::binary);request<<J{{"model_name",utf8(model_name)},{"command",command},{"curve_ids",curves}}.dump(2);request.close();
 ProToolkitDllHandle module=nullptr;ProError initialized=PRO_TK_NO_ERROR;ProName display;wcscpy_s(display,L"MCP_CREO_MechDog Blend");ProCharPath dll,textdir;
 strcpy_s(dll,utf8((callback_dir/L"callback.dll").wstring()).c_str());strcpy_s(textdir,utf8(callback_dir.wstring()).c_str());
 ProError loaded=ProToolkitDllLoad(display,dll,textdir,PRO_B_FALSE,&module,&initialized,nullptr);log("BLEND_DLL_LOAD=%d INITIALIZE=%d\n",loaded,initialized);
 try{
  check(loaded,"LoadBlendSelectionCallback");
  check(initialized,"InitializeBlendSelectionCallback");
  std::wstring macro=L"~ Command `ProCmdFtPBlend`; ~ Activate `main_dlg_cur` `chkbn.blend_sectionspage.0` 1; ~ Select `blend_sectionspage.0.0` `PH.sketchselopt` 1 `Selected`; ~ Activate `UI Message Dialog` `confirm`;";
  for(size_t i=0;i<curves.size();i++){
   if(i)macro+=L"~ Activate `blend_sectionspage.0.0` `PH.insertbtn`;";
   macro+=L"~ Focus `blend_sectionspage.0.0` `PH.curve_coll_repr`; ~ Select `blend_sectionspage.0.0` `PH.curve_coll_repr` 0; ~ Activate `blend_sectionspage.0.0` `PH.chain_btn`; ~ Select `chain_dlg` `ChainMethod` 1 `others`; ~ Select `chain_dlg` `RuleOptions` 1 `all_curves_in_feature`; ~ Command `"+wide(command)+L"`; ~ Activate `chain_dlg` `OKButton`;";
  }
  macro+=L"~ Activate `main_dlg_cur` `chkbn.blend_optionspage.0` 1; ~ Select `blend_optionspage.0.0` `PH.blendoptions` 1 `"+wide(op.value("interpolation","straight")=="smooth"?"Smooth":"Straight")+L"`; ~ Activate `main_dlg_cur` `dashInst0.Done`; ~ Activate `main_dlg_cur` `dashInst0.Quit`; ~ Activate `UI Message Dialog` `yes`;";
  CK(ProMacroLoad(macro.data()));J after=inspection();
  std::ifstream file(callback_dir/L"callback_result.json");J selected;file>>selected;
  if(selected.value("selected",0)!=(int)curves.size()||selected.value("exception",false))throw std::runtime_error("Blend callback did not select every section; inspect callback_result.json");
  std::set<int> original;for(auto f:before["features"])original.insert(f["id"].get<int>());std::vector<int> candidates;
  for(auto f:after["features"])if(!original.count(f["id"])&&f["type"].get<int>()==PRO_FEAT_PROTRUSION){ProFeature native;CK(ProFeatureInit((ProSolid)board,f["id"],&native));ProLine subtype;CK(ProFeatureSubtypeGet(&native,subtype));if(!wcscmp(subtype,L"\u6df7\u5408")||!_wcsicmp(subtype,L"Blend"))candidates.push_back(native.id);}
  if(candidates.size()!=1)throw std::runtime_error("Blend command did not create exactly one active native solid Blend");
  ProFeature created;CK(ProFeatureInit((ProSolid)board,candidates[0],&created));int count=0;CK(ProFeatureNumSectionsGet(&created,&count));if(count!=(int)curves.size())throw std::runtime_error("Created Blend section count differs from request");
  if(read_blend_setting(created.id,L"created")["interpolation"]!=op.value("interpolation","straight"))throw std::runtime_error("Created Blend interpolation differs from request");
  ProName label;wcscpy_s(label,wide(op["label"]).c_str());CK(ProModelitemNameSet(&created,label));
  remember(op,created,{{"sections",op["sections"]},{"interpolation",op.value("interpolation","straight")},{"construction","native_blend_synchronous_selection"}});
 }catch(...){if(module)ProToolkitDllUnload(module);throw;}
 CK(ProToolkitDllUnload(module));
}
