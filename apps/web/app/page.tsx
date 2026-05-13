import { SignInButton, SignedIn, SignedOut, UserButton } from "@clerk/nextjs";
import Link from "next/link";

export default function HomePage() {
  return (
    <main className="container">
      <h1>RealtyOps OS</h1>
      <p>Demo bootstrap: Clerk-authenticated dashboard + API/worker controls.</p>
      <SignedOut>
        <SignInButton mode="modal">
          <button>Sign In</button>
        </SignInButton>
      </SignedOut>
      <SignedIn>
        <div style={{ display: "flex", gap: 12, alignItems: "center" }}>
          <Link href="/dashboard">Go to Dashboard</Link>
          <UserButton />
        </div>
      </SignedIn>
    </main>
  );
}
