"use client";

import { SignInButton, UserButton, useUser } from "@clerk/nextjs";
import Link from "next/link";

export default function HomePage() {
  const { isLoaded, isSignedIn } = useUser();

  return (
    <main className="container">
      <h1>RealtyOps OS</h1>
      <p>Demo bootstrap: Clerk-authenticated dashboard + API/worker controls.</p>
      {!isLoaded ? <p>Loading...</p> : null}
      {isLoaded && !isSignedIn ? (
        <SignInButton mode="modal">
          <button>Sign In</button>
        </SignInButton>
      ) : null}
      {isLoaded && isSignedIn ? (
        <div style={{ display: "flex", gap: 12, alignItems: "center" }}>
          <Link href="/dashboard">Go to Dashboard</Link>
          <UserButton />
        </div>
      ) : null}
    </main>
  );
}
