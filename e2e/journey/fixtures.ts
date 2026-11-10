import { test as base } from "@playwright/test";
import { installIntroTourSeenSeed } from "../helpers/intro-tour";

type IntroTourFixtures = {
  /** When true (default), mark the intro tour as seen before each test. */
  seedIntroTourDone: boolean;
};

export const test = base.extend<IntroTourFixtures>({
  seedIntroTourDone: [true, { option: true }],
  page: async ({ page, seedIntroTourDone }, use) => {
    if (seedIntroTourDone) {
      await installIntroTourSeenSeed(page);
    }
    await use(page);
  },
});

export { expect } from "@playwright/test";
export type { Page, Route } from "@playwright/test";
