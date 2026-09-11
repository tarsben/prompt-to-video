import {Composition} from 'remotion';

// Overwritten per job by the orchestrator (_write_root).
// Placeholder so `npm install` / typechecks have a valid entrypoint.
export const RemotionRoot = () => (
  <>
    <Composition
      id="placeholder"
      component={() => null}
      durationInFrames={30}
      fps={30}
      width={1920}
      height={1080}
    />
  </>
);
