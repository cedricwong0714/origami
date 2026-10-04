"""SBML Level 2 for the three kinetics modes already in ORIGAMI.

Rates are taken from the request or from tagged literature slots.
No new biological constants are introduced here.
"""

from __future__ import annotations

from xml.sax.saxutils import escape

from origami.kinetics.rates import apply_user_rates, default_rate_slots
from origami.kinetics.simulate import KineticsSimError


def _f(value: float) -> str:
    return f"{float(value):.8g}"


def _numeric(slots: list, name: str) -> float | None:
    for slot in slots:
        if slot.name == name:
            return None if slot.value is None else float(slot.value)
    return None


def recruitment_sbml(*, kd_M: float, c_free_M: float, kon_per_M_s: float | None) -> str:
    """Langmuir occupancy. Time course only if kon is supplied."""
    if kd_M <= 0 or c_free_M < 0:
        raise KineticsSimError("Kd must be > 0 and C_free >= 0")
    koff = None if kon_per_M_s is None else float(kon_per_M_s) * float(kd_M)
    notes = (
        "d theta/dt = kon * C_free * (1 - theta) - koff * theta; "
        "koff = kon * Kd; theta_ss = C_free / (C_free + Kd). "
        "calibrated=false."
    )
    params = [
        ("Kd", kd_M, "M"),
        ("C_free", c_free_M, "M"),
    ]
    if kon_per_M_s is not None:
        params.append(("kon", kon_per_M_s, "1/M/s"))
        params.append(("koff", koff, "1/s"))
    param_xml = "\n".join(
        f'      <parameter id="{name}" value="{_f(val)}" units="{units}" constant="true"/>'
        for name, val, units in params
    )
    if kon_per_M_s is None:
        kinetic = "C_free / (C_free + Kd)"
        assignment = (
            "    <listOfRules>\n"
            '      <assignmentRule variable="theta">\n'
            f"        <math xmlns=\"http://www.w3.org/1998/Math/MathML\"><ci>steady</ci></math>\n"
            "      </assignmentRule>\n"
            "    </listOfRules>\n"
        )
        # Keep assignment readable without MathML ci name mismatch: use notes + initial.
        assignment = ""
        species_init = _f(c_free_M / (c_free_M + kd_M))
        reactions = ""
    else:
        assignment = ""
        species_init = "0"
        reactions = (
            "    <listOfReactions>\n"
            '      <reaction id="bind" reversible="true">\n'
            "        <listOfReactants>\n"
            '          <speciesReference species="theta_empty" stoichiometry="1"/>\n'
            "        </listOfReactants>\n"
            "        <listOfProducts>\n"
            '          <speciesReference species="theta" stoichiometry="1"/>\n'
            "        </listOfProducts>\n"
            "        <kineticLaw>\n"
            '          <math xmlns="http://www.w3.org/1998/Math/MathML">\n'
            "            <apply><minus/>\n"
            "              <apply><times/><ci>kon</ci><ci>C_free</ci><ci>theta_empty</ci></apply>\n"
            "              <apply><times/><ci>koff</ci><ci>theta</ci></apply>\n"
            "            </apply>\n"
            "          </math>\n"
            "        </kineticLaw>\n"
            "      </reaction>\n"
            "    </listOfReactions>\n"
        )
    empty_init = "1" if kon_per_M_s is not None else _f(1.0 - c_free_M / (c_free_M + kd_M))
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<sbml xmlns="http://www.sbml.org/sbml/level2/version4" level="2" version="4">\n'
        f'  <model id="origami_recruitment" name="ORIGAMI recruitment Langmuir">\n'
        f"    <notes><body xmlns=\"http://www.w3.org/1999/xhtml\">{escape(notes)}</body></notes>\n"
        "    <listOfCompartments>\n"
        '      <compartment id="cell" size="1" constant="true"/>\n'
        "    </listOfCompartments>\n"
        "    <listOfSpecies>\n"
        f'      <species id="theta" compartment="cell" initialAmount="{species_init}" hasOnlySubstanceUnits="true"/>\n'
        f'      <species id="theta_empty" compartment="cell" initialAmount="{empty_init}" hasOnlySubstanceUnits="true"/>\n'
        "    </listOfSpecies>\n"
        "    <listOfParameters>\n"
        f"{param_xml}\n"
        "    </listOfParameters>\n"
        f"{assignment}{reactions}"
        "  </model>\n"
        "</sbml>\n"
    )


def spy_sbml(*, k_on: float, tag0_M: float, catcher0_M: float) -> str:
    if k_on <= 0 or tag0_M < 0 or catcher0_M < 0:
        raise KineticsSimError("Spy k_on must be > 0 and concentrations >= 0")
    notes = (
        "Lumped irreversible bimolecular adduct. d adduct/dt = k_on * tag * catcher. "
        "Zakeri 2012 lumped k_on when that slot is used. calibrated=false."
    )
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<sbml xmlns="http://www.sbml.org/sbml/level2/version4" level="2" version="4">\n'
        '  <model id="origami_spy_lumped" name="ORIGAMI Spy lumped adduct">\n'
        f"    <notes><body xmlns=\"http://www.w3.org/1999/xhtml\">{escape(notes)}</body></notes>\n"
        "    <listOfCompartments><compartment id=\"cell\" size=\"1\" constant=\"true\"/></listOfCompartments>\n"
        "    <listOfSpecies>\n"
        f'      <species id="tag" compartment="cell" initialConcentration="{_f(tag0_M)}"/>\n'
        f'      <species id="catcher" compartment="cell" initialConcentration="{_f(catcher0_M)}"/>\n'
        '      <species id="adduct" compartment="cell" initialConcentration="0"/>\n'
        "    </listOfSpecies>\n"
        "    <listOfParameters>\n"
        f'      <parameter id="k_on" value="{_f(k_on)}" units="1/M/s" constant="true"/>\n'
        "    </listOfParameters>\n"
        "    <listOfReactions>\n"
        '      <reaction id="capture" reversible="false">\n'
        "        <listOfReactants>\n"
        '          <speciesReference species="tag" stoichiometry="1"/>\n'
        '          <speciesReference species="catcher" stoichiometry="1"/>\n'
        "        </listOfReactants>\n"
        "        <listOfProducts>\n"
        '          <speciesReference species="adduct" stoichiometry="1"/>\n'
        "        </listOfProducts>\n"
        "        <kineticLaw>\n"
        '          <math xmlns="http://www.w3.org/1998/Math/MathML">\n'
        "            <apply><times/><ci>k_on</ci><ci>tag</ci><ci>catcher</ci></apply>\n"
        "          </math>\n"
        "        </kineticLaw>\n"
        "      </reaction>\n"
        "    </listOfReactions>\n"
        "  </model>\n"
        "</sbml>\n"
    )


def nanobit_sbml(*, k_on: float, k_off: float, lg_M: float, sm_M: float) -> str:
    if k_on <= 0 or k_off < 0 or lg_M < 0 or sm_M < 0:
        raise KineticsSimError("NanoBiT rates must be finite and concentrations >= 0")
    notes = (
        "Reversible LgBiT + SmBiT = complex. Rates from caller or literature slots. "
        "calibrated=false."
    )
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<sbml xmlns="http://www.sbml.org/sbml/level2/version4" level="2" version="4">\n'
        '  <model id="origami_nanobit" name="ORIGAMI NanoBiT complementation">\n'
        f"    <notes><body xmlns=\"http://www.w3.org/1999/xhtml\">{escape(notes)}</body></notes>\n"
        "    <listOfCompartments><compartment id=\"cell\" size=\"1\" constant=\"true\"/></listOfCompartments>\n"
        "    <listOfSpecies>\n"
        f'      <species id="Lg" compartment="cell" initialConcentration="{_f(lg_M)}"/>\n'
        f'      <species id="Sm" compartment="cell" initialConcentration="{_f(sm_M)}"/>\n'
        '      <species id="complex" compartment="cell" initialConcentration="0"/>\n'
        "    </listOfSpecies>\n"
        "    <listOfParameters>\n"
        f'      <parameter id="k_on" value="{_f(k_on)}" units="1/M/s" constant="true"/>\n'
        f'      <parameter id="k_off" value="{_f(k_off)}" units="1/s" constant="true"/>\n'
        "    </listOfParameters>\n"
        "    <listOfReactions>\n"
        '      <reaction id="complement" reversible="true">\n'
        "        <listOfReactants>\n"
        '          <speciesReference species="Lg" stoichiometry="1"/>\n'
        '          <speciesReference species="Sm" stoichiometry="1"/>\n'
        "        </listOfReactants>\n"
        "        <listOfProducts>\n"
        '          <speciesReference species="complex" stoichiometry="1"/>\n'
        "        </listOfProducts>\n"
        "        <kineticLaw>\n"
        '          <math xmlns="http://www.w3.org/1998/Math/MathML">\n'
        "            <apply><minus/>\n"
        "              <apply><times/><ci>k_on</ci><ci>Lg</ci><ci>Sm</ci></apply>\n"
        "              <apply><times/><ci>k_off</ci><ci>complex</ci></apply>\n"
        "            </apply>\n"
        "          </math>\n"
        "        </kineticLaw>\n"
        "      </reaction>\n"
        "    </listOfReactions>\n"
        "  </model>\n"
        "</sbml>\n"
    )


def sbml_from_kinetics_body(body: dict) -> str:
    """Build SBML for one existing kinetics mode. Does not add a new ODE."""
    mode = body.get("mode")
    merged = dict(body.get("rates") or {})
    for key in (
        "spy_k_on_per_M_s",
        "nanobit_k_on_per_M_s",
        "nanobit_k_off_per_s",
        "cam_m13_kd_M",
    ):
        if key in body and key not in merged:
            merged[key] = body[key]
    slots = apply_user_rates(default_rate_slots(), merged)
    if mode == "recruitment_steady":
        kd = _numeric(slots, "cam_m13_kd_M")
        if kd is None:
            raise KineticsSimError("cam_m13_kd_M is vacant")
        if "c_free_M" not in body:
            raise KineticsSimError("c_free_M is required")
        kon = body.get("kon_per_M_s")
        if kon is not None:
            kon = float(kon)
        return recruitment_sbml(kd_M=kd, c_free_M=float(body["c_free_M"]), kon_per_M_s=kon)
    if mode == "covalent_timecourse":
        k_on = _numeric(slots, "spy_k_on_per_M_s")
        if k_on is None:
            raise KineticsSimError("spy_k_on_per_M_s is vacant")
        tag0 = float(body.get("tag0_M", 10e-6))
        catcher0 = float(body.get("catcher0_M", 10e-6))
        return spy_sbml(k_on=k_on, tag0_M=tag0, catcher0_M=catcher0)
    if mode == "nanobit_complementation":
        k_on = _numeric(slots, "nanobit_k_on_per_M_s")
        k_off = _numeric(slots, "nanobit_k_off_per_s")
        if k_on is None or k_off is None:
            raise KineticsSimError("NanoBiT k_on and k_off are required")
        if "lg0_M" not in body or "sm0_M" not in body:
            raise KineticsSimError("nanobit_complementation requires lg0_M and sm0_M")
        return nanobit_sbml(
            k_on=k_on,
            k_off=k_off,
            lg_M=float(body["lg0_M"]),
            sm_M=float(body["sm0_M"]),
        )
    raise KineticsSimError(
        "mode must be recruitment_steady, covalent_timecourse, or nanobit_complementation"
    )
