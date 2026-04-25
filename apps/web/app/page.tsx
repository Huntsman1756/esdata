import { Suspense } from "react";
import ConsultaClient from "@/components/consulta-client";

export default function Home() {
  return (
    <Suspense>
      <ConsultaClient />
    </Suspense>
  );
}
