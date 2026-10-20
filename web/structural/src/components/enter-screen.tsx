import Image from "next/image";
import Link from "next/link";

export function EnterScreen() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center gap-14 px-6 py-16">
      <Image
        src="/origami-wordmark.png"
        alt="ORIGAMI"
        width={880}
        height={256}
        priority
        className="h-auto w-[min(94vw,920px)]"
      />
      <Link
        href="/models"
        className="rounded-full bg-studio-button px-10 py-3.5 text-lg font-medium text-studio-button-text"
      >
        Enter the software
      </Link>
    </main>
  );
}
