// Helical thread modelling.
//
// Creo's dedicated helical-sweep feature exposes PRO_E_HLSWP_* element ids in
// ProElemId.h, but no header documents that tree and no PRO_HLSWP_* value enums
// exist anywhere in the Pro/TOOLKIT SDK, so the feature cannot be assembled from
// documented input. The supported route is two documented features:
//   1. a datum curve from equation (PRO_CURVE_TYPE_FROM_EQUATION, ProDtmCrv.h)
//      carrying the helix,
//   2. a constant-section sweep (PRO_SWEEP, ProSweep.h) whose trajectory is that
//      curve chain.
// Included from generic.cpp after the shared helpers and after advanced.cpp.

static const wchar_t *kHelixEquationSuffix = L"";

// Cylindrical equations use r/theta/z with theta in degrees, which is the form
// Creo's equation editor expects for a axisymmetric helix. Cartesian output is
// provided for models whose reference csys axis must be picked explicitly.
static std::wstring helix_equations(double radius, double pitch, double length, double start_z,
                                    bool right_hand, bool cartesian) {
    double turns = length / pitch;
    double direction = right_hand ? 1.0 : -1.0;
    wchar_t buffer[512];
    if (cartesian) {
        const double two_pi = 6.283185307179586;
        double sweep = direction * two_pi * turns;
        swprintf_s(buffer,
                   L"x = %.9f*cos(%.12f*t)\n"
                   L"y = %.9f*sin(%.12f*t)\n"
                   L"z = %.9f+%.9f*t",
                   radius, sweep, radius, sweep, start_z, length);
    } else {
        swprintf_s(buffer,
                   L"r = %.9f\n"
                   L"theta = %.9f*t\n"
                   L"z = %.9f+%.9f*t",
                   radius, direction * 360.0 * turns, start_z, length);
    }
    return buffer;
}

static void generic_equation_curve(const J &op) {
    ProElement root = node(nullptr, PRO_E_FEATURE_TREE);
    integer(root, PRO_E_FEATURE_TYPE, PRO_FEAT_CURVE);
    integer(root, PRO_E_CURVE_TYPE, PRO_CURVE_TYPE_FROM_EQUATION);
    text(root, PRO_E_STD_FEATURE_NAME, wide(op["label"]).c_str());
    ProSelection csys = resolve(op.value("reference_csys", J{{"kind", "default_csys"}}));
    ref(root, PRO_E_CRV_FR_EQ_REF_CSYS, csys);
    ProSelectionFree(&csys);
    std::string system = op.value("system", "cylindrical");
    integer(root, PRO_E_CRV_FR_EQ_CSYS_TYPE,
            system == "cartesian"    ? PRO_CRV_FR_EQ_CSYS_TYPE_CARTESIAN
            : system == "spherical"  ? PRO_CRV_FR_EQ_CSYS_TYPE_SPHERICAL
                                     : PRO_CRV_FR_EQ_CSYS_TYPE_CYLINDRICAL);
    real(root, PRO_E_CRV_FR_EQ_PARAM_MIN, op.value("param_min", 0.0));
    real(root, PRO_E_CRV_FR_EQ_PARAM_MAX, op.value("param_max", 1.0));
    std::wstring equations = wide(op["equations"]);
    CK(ProElementWstringSet(node(root, PRO_E_CRV_ENTER_EQUATION), equations.data()));
    log("EQUATION_CURVE system=%s equations=%s\n", system.c_str(), op["equations"].dump().c_str());
    ProFeature f = create(root);
    CK(ProElementFree(&root));
    CK(ProSolidRegenerate((ProSolid)board, PRO_REGEN_NO_FLAGS));
    J ids = J::array();
    CK(ProFeatureGeomitemVisit(&f, PRO_CURVE, collect_geom_ids, nullptr, &ids));
    if (ids.empty())
        throw std::runtime_error("The equation curve created no native curve geometry; check the "
                                 "equations against the reference coordinate system");
    log("EQUATION_CURVE_CURVES=%d\n", (int)ids.size());
    remember(op, f, {{"curve_ids", ids}, {"equations", op["equations"]}, {"system", system}});
}

static void generic_helical_sweep(const J &op) {
    std::string label = op.at("label");
    std::string curve_label = label.size() > 22 ? label.substr(0, 22) + "_helix" : label + "_helix";
    bool cartesian = op.value("system", "cylindrical") == "cartesian";
    J curve_op = {{"op", "datum_curve_equation"},
                  {"label", curve_label},
                  {"system", op.value("system", "cylindrical")},
                  {"param_min", op.value("param_min", 0.0)},
                  {"param_max", op.value("param_max", 1.0)}};
    curve_op["equations"] =
        op.contains("equations")
            ? op["equations"]
            : J(utf8(helix_equations(op.at("radius"), op.at("pitch"), op.at("length"),
                                     op.value("start_z", 0.0),
                                     op.value("hand", "right") == "right", cartesian)));
    if (op.contains("reference_csys"))
        curve_op["reference_csys"] = op["reference_csys"];
    generic_equation_curve(curve_op);

    J sweep_op = {{"op", "sweep"},
                  {"label", label},
                  {"trajectory", curve_label},
                  {"profile", op.at("profile")},
                  {"dimensions", op.value("dimensions", J::array())},
                  {"constraints", op.value("constraints", J::array())},
                  {"mode", op.value("mode", "cut")}};
    if (op.contains("thin"))
        sweep_op["thin"] = op["thin"];
    if (op.contains("frame_normal"))
        sweep_op["frame_normal"] = op["frame_normal"];
    if (op.contains("frame_orient"))
        sweep_op["frame_orient"] = op["frame_orient"];
    if (op.contains("frame_user_x"))
        sweep_op["frame_user_x"] = op["frame_user_x"];
    if (op.contains("frame_pivot_direction"))
        sweep_op["frame_pivot_direction"] = op["frame_pivot_direction"];
    if (op.contains("frame_z_direction"))
        sweep_op["frame_z_direction"] = op["frame_z_direction"];
    if (op.contains("frame_start_x_direction"))
        sweep_op["frame_start_x_direction"] = op["frame_start_x_direction"];
    log("HELICAL_SWEEP curve=%s mode=%s\n", curve_label.c_str(),
        sweep_op["mode"].get<std::string>().c_str());
    generic_sweep(sweep_op);
}
