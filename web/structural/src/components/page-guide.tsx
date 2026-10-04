/** Shared layout for studio page copy. Short intro, then steps and how to read the numbers. */
export function PageGuide({
  intro,
  steps,
  read,
  rules,
  next,
}: {
  intro: string;
  steps: string[];
  read: string[];
  rules: string[];
  next: string[];
}) {
  const blocks = [
    { title: "How to use it", items: steps },
    { title: "How to read the numbers", items: read },
    { title: "What the software decides", items: rules },
    { title: "What to do next", items: next },
  ];
  return (
    <div className="mt-4 max-w-2xl space-y-5 text-sm leading-relaxed text-studio-muted">
      <p className="text-[15px] leading-relaxed text-studio-foreground">{intro}</p>
      {blocks.map((block) => (
        <section key={block.title}>
          <h2 className="text-sm font-semibold text-studio-foreground">{block.title}</h2>
          <ul className="mt-2 list-disc space-y-1 pl-5">
            {block.items.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </section>
      ))}
    </div>
  );
}
