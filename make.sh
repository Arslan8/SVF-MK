cd Debug-build/
make symex -j200 && make thread_discovery -j200 && make svf-ex -j200 && cd ../  #run4 for normal , run_discovery for only thread discovery, maybe in future all analysis might be different executables.
