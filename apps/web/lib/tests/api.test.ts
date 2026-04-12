import { describe, it, expect } from "vitest";
import * as api from "../api";

describe("api client config", () => {
  it("exports all expected fetch functions", () => {
    expect(typeof api.getStatus).toBe("function");
    expect(typeof api.searchLegislacion).toBe("function");
    expect(typeof api.searchDoctrina).toBe("function");
    expect(typeof api.getDoctrina).toBe("function");
    expect(typeof api.getCobertura).toBe("function");
    expect(typeof api.getArticulo).toBe("function");
    expect(typeof api.getArticuloHistorial).toBe("function");
    expect(typeof api.getNormas).toBe("function");
  });
});
