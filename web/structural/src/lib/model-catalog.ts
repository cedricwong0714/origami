export type ModelEntry = {
  href: string;
  title: string;
  summary: string;
};

export type ModelGroup = {
  title: string;
  blurb: string;
  models: ModelEntry[];
};

/** Every studio screen that runs or explains a model. One list, used by the chooser. */
export const MODEL_GROUPS: ModelGroup[] = [
  {
    title: "Structural analysis",
    blurb: "Shape of the CTPR screw and which repeat count to build next.",
    models: [
      {
        href: "/scaffold",
        title: "3D scaffold",
        summary: "Helical coordinates of the repeats, drawn as a screw.",
      },
      {
        href: "/present",
        title: "Compare lengths",
        summary: "The same constructs side by side.",
      },
      {
        href: "/design",
        title: "Choose a length",
        summary: "Docking score from n = 3 to 24.",
      },
      {
        href: "/docking/geometry",
        title: "Distance and clash",
        summary: "End-to-end chord and whether two payloads collide.",
      },
      {
        href: "/learn",
        title: "Next length",
        summary: "Gaussian process on the lengths you enter, then the next assay.",
      },
    ],
  },
  {
    title: "Stability confirmation",
    blurb: "Whether the scaffold stays folded at the assay temperature.",
    models: [
      {
        href: "/stability",
        title: "Stay folded?",
        summary: "Melting temperature against repeat count, with a 37°C line.",
      },
      {
        href: "/stability/calculator",
        title: "Energy vs temperature",
        summary: "Gibbs energy from the DSC fit, across temperature.",
      },
    ],
  },
  {
    title: "Docking verification",
    blurb: "Whether the sensing pair is occupied at one scaffold length.",
    models: [
      {
        href: "/docking",
        title: "Will it bind?",
        summary: "Affinity check at a single repeat count.",
      },
    ],
  },
  {
    title: "Kinetic modelling",
    blurb: "Three time or occupancy calculations. Each one is its own screen.",
    models: [
      {
        href: "/kinetics",
        title: "How much is bound?",
        summary: "Langmuir occupancy of CaM–M13 at a free concentration.",
      },
      {
        href: "/kinetics/spy",
        title: "Spy lock",
        summary: "SpyTag–SpyCatcher covalent time course.",
      },
      {
        href: "/kinetics/nanobit",
        title: "Light reporter",
        summary: "LgBiT–SmBiT complementation.",
      },
    ],
  },
  {
    title: "One construct, lab entry, and the map",
    blurb: "Screens that combine the models, or record a measurement.",
    models: [
      {
        href: "/ssdk",
        title: "One length",
        summary: "Structure, stability, docking, and one kinetic mode at a single n.",
      },
      {
        href: "/wizard",
        title: "Step through one length",
        summary: "The same report, one step at a time, with a downloadable summary.",
      },
      {
        href: "/lab",
        title: "Lab numbers",
        summary: "Enter a plate-style reading and see the residual against the model.",
      },
      {
        href: "/intake",
        title: "Data intake",
        summary: "Check a table before it is used as a training row.",
      },
      {
        href: "/guide",
        title: "What you can run",
        summary: "Which calculations have numbers, and which still need a measurement.",
      },
    ],
  },
];
