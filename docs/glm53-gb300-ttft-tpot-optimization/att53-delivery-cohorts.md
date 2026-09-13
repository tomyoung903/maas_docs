# Tool-call delivery and original-output latency

ATT53 warmup completed100/100 successfully.28requests have equal first/last generation timestamps;all28ended tool_calls. Their median output was59.5tokens,max3574,and TTFTmedian3.913s,max33.920s. The72 positive-spanresponses had TTFTmedian2.604s,max5.066s. This is an observed association,not a causalcomparison.

The Alex source counts content,reasoning_content,reasoning,tool_calls andfunction_call fragments. Zero-spanTPOT therefore must not be interpreted as infinite engine output speed. Canonical Alexstatistics keep everyrequest; the analysis separately reports positive-spanTPOT and finiteOTPS.

The recorded deployment selects Dynamo chatprocessing/GLM47toolparsing. The frozenRust jail source buffers incomplete toolcalls until marker/parsercompletion and passes reasoningchunks. This is consistent with the deliverypattern. Exactcompiledparser provenance and request-leveltrace attribution remain incomplete; buffering,networkcoalescing and serveroutput behavior are not separated by the slimclientevents alone.

No serving/generator/payload change. Originaloutputpolicies and strictTTFTgoal remain intact. SeeWARMUP-OBSERVATION.json and../../replay/warmup-original-output-analysis.json for exactcohorts/hashes.
