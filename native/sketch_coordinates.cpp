// Complete coordinate dimensions for exact, fully supplied profile geometry.
// Accepted native profiles include large polygons, axis-aligned/rotated arcs and circles.
static std::string profile_dimensioning(const J& op){
 std::string requested=op.value("dimensioning","auto");if(requested!="auto")return requested;
 if(!op.value("dimensions",J::array()).empty()||!op.value("constraints",J::array()).empty())return "autodim";
 if(op.contains("plane")&&!op["plane"].is_string())return "autodim";
 double extent=0;int count=0;for(auto e:op.at("entities")){std::string type=e.at("type");if(type!="line"&&type!="centerline"&&type!="rectangle"&&type!="polyline"&&type!="circle"&&type!="arc")return "autodim";
  count+=type=="rectangle"?4:type=="polyline"?(int)e["points"].size()-1+(e.value("closed",false)?1:0):1;
  for(auto key:{"start","end","min","max","center"})if(e.contains(key))for(auto value:e[key])extent=std::max(extent,fabs(value.get<double>()));
  if(e.contains("points"))for(auto point:e["points"])for(auto value:point)extent=std::max(extent,fabs(value.get<double>()));
  if(e.contains("radius"))extent=std::max(extent,e["radius"].get<double>());
 }
 return count>=10||extent>1000?"coordinates":"autodim";
}
static J coordinate_dimensions(ProSection section,int origin,const std::map<std::string,int>& entities,const std::array<int,2>& axes,const std::vector<int>& anchors){
 CK(ProSectionEpsilonSet(section,0.000000001));
 J dimensions=J::object(),snapshot=J::array();
 for(auto item:entities){Pro2dEntdef* def=nullptr;CK(ProSectionEntityGet(section,item.second,&def));J row={{"name",item.first},{"id",item.second},{"type",(int)def->type}};
  if(def->type==PRO_2D_LINE||def->type==PRO_2D_CENTER_LINE){auto line=(Pro2dLinedef*)def;row["points"]={{{"sense",PRO_ENT_START},{"key","start"},{"xy",{line->end1[0],line->end1[1]}}},{{"sense",PRO_ENT_END},{"key","end"},{"xy",{line->end2[0],line->end2[1]}}}};}
  else if(def->type==PRO_2D_CIRCLE){auto circle=(Pro2dCircledef*)def;row["points"]={{{"sense",PRO_ENT_CENTER},{"key","center"},{"xy",{circle->center[0],circle->center[1]}}}};row["radius"]=circle->radius;}
  else if(def->type==PRO_2D_ARC){auto arc=(Pro2dArcdef*)def;row["points"]={{{"sense",PRO_ENT_CENTER},{"key","center"},{"xy",{arc->center[0],arc->center[1]}}}};row["radius"]=arc->radius;row["angles"]={arc->start_angle,arc->end_angle};}
  else throw std::runtime_error("Coordinate dimensioning accepts lines, polylines, rectangles, circles and arcs only");
  snapshot.push_back(row);
 }
 for(auto row:snapshot){int entity=row["id"];std::string prefix="coord_"+row["name"].get<std::string>();
  for(auto point:row["points"])for(int label_axis=0;label_axis<2;label_axis++){
   int axis=axes[label_axis],ids[]={origin,entity},dim;ProSectionPointType endpoint=(ProSectionPointType)point["sense"].get<int>(),points[]={PRO_ENT_CENTER,endpoint};double value=point["xy"][axis];
   if(endpoint==PRO_ENT_END&&row["points"].size()==2&&fabs(value-row["points"][0]["xy"][axis].get<double>())<1e-12){log("COORDINATE_AXIS_LINE_SHARED=%s axis=%d\n",prefix.c_str(),axis);continue;}
   ProSecdimType type=axis?PRO_TK_DIM_PNT_PNT_VERT:PRO_TK_DIM_PNT_PNT_HORIZ;
   if(endpoint==PRO_ENT_CENTER&&fabs(value)<1e-10)for(int anchor:anchors){Pro2dEntdef* def=nullptr;CK(ProSectionEntityGet(section,anchor,&def));if(def->type!=PRO_2D_LINE&&def->type!=PRO_2D_CENTER_LINE)continue;auto line=(Pro2dLinedef*)def;
    if(fabs(line->end1[axis]-line->end2[axis])<1e-8&&fabs(line->end1[axis])<1e-8){ids[0]=anchor;points[0]=PRO_ENT_WHOLE;type=PRO_TK_DIM_LINE_POINT;break;}
   }
   Pro2dPnt place={point["xy"][0],point["xy"][1]};CK(ProSecdimCreate(section,ids,points,2,type,place,&dim));CK(ProSecdimValueSet(section,dim,fabs(value)));
   dimensions[prefix+"_"+point["key"].get<std::string>()+(label_axis?"_y":"_x")]=dim;
  }
  if(row.contains("radius")){ProSectionPointType whole=PRO_ENT_WHOLE;int dim;Pro2dPnt place={0,0};CK(ProSecdimCreate(section,&entity,&whole,1,PRO_TK_DIM_RAD,place,&dim));CK(ProSecdimValueSet(section,dim,row["radius"]));dimensions[prefix+"_radius"]=dim;}
  if(row.contains("angles"))for(int i=0;i<2;i++){
   int ids[]={entity,entity},dim;ProSectionPointType points[]={PRO_ENT_CENTER,i?PRO_ENT_END:PRO_ENT_START};double angle=row["angles"][i],radius=row["radius"];
   Pro2dPnt place={row["points"][0]["xy"][0].get<double>()+radius*cos(angle),row["points"][0]["xy"][1].get<double>()+radius*sin(angle)};
   CK(ProSecdimCreate(section,ids,points,2,PRO_TK_DIM_ANG_POLAR,place,&dim));double degrees;CK(ProSecdimValueGet(section,dim,&degrees));log("COORDINATE_ARC_POLAR=%s_%d value=%.12f\n",prefix.c_str(),i,degrees);
   if(fabs(remainder(degrees*acos(-1.0)/180-angle,2*acos(-1.0)))>1e-8)throw std::runtime_error("Native polar dimension does not match the supplied arc angle");
   CK(ProSecdimValueSet(section,dim,degrees));
   dimensions[prefix+(i?"_end_angle":"_start_angle")]=dim;
  }
 }
 return {{"dimension_ids",dimensions},{"targets",snapshot},{"origin_id",origin}};
}
static J verify_coordinate_plan(ProSection section,const J& targets,int origin){
 double deviation=0;int points=0;
 Pro2dEntdef* coordinate=nullptr;CK(ProSectionEntityGet(section,origin,&coordinate));auto cs=(Pro2dCoordSysdef*)coordinate;log("COORDINATE_ORIGIN=%.12f,%.12f\n",cs->pnt[0],cs->pnt[1]);
 for(auto row:targets){Pro2dEntdef* def=nullptr;CK(ProSectionEntityGet(section,row["id"],&def));if((int)def->type!=row["type"].get<int>())throw std::runtime_error("Coordinate dimensioning changed an entity type");
  for(auto point:row["points"]){double* actual=nullptr;if(def->type==PRO_2D_CIRCLE)actual=((Pro2dCircledef*)def)->center;else if(def->type==PRO_2D_ARC)actual=((Pro2dArcdef*)def)->center;else actual=point["sense"].get<int>()==PRO_ENT_START?((Pro2dLinedef*)def)->end1:((Pro2dLinedef*)def)->end2;
   for(int axis=0;axis<2;axis++)deviation=std::max(deviation,fabs(actual[axis]-point["xy"][axis].get<double>()));points++;
  }
  if(row.contains("radius"))deviation=std::max(deviation,fabs((def->type==PRO_2D_ARC?((Pro2dArcdef*)def)->radius:((Pro2dCircledef*)def)->radius)-row["radius"].get<double>()));
  if(row.contains("angles")){auto arc=(Pro2dArcdef*)def;double actual[]={arc->start_angle,arc->end_angle};for(int i=0;i<2;i++)deviation=std::max(deviation,row["radius"].get<double>()*fabs(remainder(actual[i]-row["angles"][i].get<double>(),2*acos(-1.0))));}
 }
 if(deviation>0.00001)throw std::runtime_error("Coordinate dimensioning changed the supplied geometry; maximum deviation mm="+std::to_string(deviation));
 return {{"point_count",points},{"max_deviation_mm",deviation},{"tolerance_mm",0.00001}};
}
