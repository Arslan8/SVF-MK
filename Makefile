all:
	./make.sh
	llvm-dis ./temp.bc

run: FORCE
	./run

dev.map:
	python3 ./parser.py 1 > dev.map

run2: dev.map FORCE
	./run2


runz: dev.map FORCE  
	./runz 

runf: FORCE
	./run3
	cp ./temp.bc  /home/arslan/stm32_discovery_arm_gcc/blinky/temp.bc
	llvm-dis ./temp.bc

#runfs: FORCE
#	./run4
#	llvm-dis ./temp.bc
#	cp ./temp.bc  ~/projects/LBC/FreeRTOS/FreeRTOS/Demo/CORTEX_M4F_STM32F407ZG-SK/build/RTOSDemo.axf.bc

runfs: FORCE
	cd partitioner && make run

runfd: FORCE
	./run4
	llvm-dis ./temp.bc

runfc: FORCE
	./run4
	llvm-dis ./temp.bc

runnfs: FORCE
	./run4
	llvm-dis ./temp.bc

FORCE:

test:
	clang-11 ./test.c -c -emit-llvm
	llvm-dis ./test.bc -o ./test.ll


exec:
	llc -filetype=obj temp.bc
	clang -g ./temp.bc

ll:
	llvm-dis ./temp.bc -o temp.ll

update:
	cp ./temp.bc /home/arslan/projects/LBC/FreeRTOS/FreeRTOS/Demo/CORTEX_M3_MPS2_QEMU_GCC/build/RTOSDemo.axf.bc

update2:
	cp ./temp.bc  /home/arslan/stm32_discovery_arm_gcc/blinky/temp.bc 

runpf:
	./partition.py -c /home/arslan/projects/LBC/FreeRTOS/FreeRTOS/Demo/CORTEX_M3_MPS2_QEMU_GCC/build/RTOSDemo.axf.bc -d ./dg 

runp:
	./partition.py -c /home/arslan/zephyrproject/zephyr/build2/build/zephyr/zephyr.elf.bc -d ./dg

ld:
	./setupLD.py -n 6 -l /home/arslan/stm32_discovery_arm_gcc/blinky/stm32_flash.overlay -c /home/arslan/stm32_discovery_arm_gcc/blinky/./autogen_data.c

ldF:
	./setupLD.py -n 20 -l ~/projects/LBC/FreeRTOS/FreeRTOS/Demo/CORTEX_M4F_STM32F407ZG-SK/./scripts/stm32_flash.overlay -c ~/projects/LBC/FreeRTOS/FreeRTOS/Demo/CORTEX_M4F_STM32F407ZG-SK/./autogen_data.c -H /home/arslan/projects/LBC/FreeRTOS/FreeRTOS/Source/portable/MemMang/autogen_heap.c

#ldFp:
#	./setupLD.py -n $(shell cat ./.policy | wc -l) -l ~/projects/LBC/FreeRTOS/FreeRTOS/Demo/CORTEX_M4F_STM32F407ZG-SK/./scripts/stm32_flash.overlay -c ~/projects/LBC/FreeRTOS/FreeRTOS/Demo/CORTEX_M4F_STM32F407ZG-SK/./autogen_data.c -H /home/arslan/projects/LBC/FreeRTOS/FreeRTOS/Source/portable/MemMang/autogen_heap.c

ldFp:
	./setupLD.py -n $(shell cat ./partitioner/out/.policy | wc -l) -l ~/projects/LBC/FreeRTOS/FreeRTOS/Demo/CORTEX_M4F_STM32F407ZG-SK/./scripts/stm32_flash.overlay -c ~/projects/LBC/FreeRTOS/FreeRTOS/Demo/CORTEX_M4F_STM32F407ZG-SK/./autogen_data.c -H /home/arslan/projects/LBC/FreeRTOS/FreeRTOS/Source/portable/MemMang/autogen_heap.c

verif:
	./checkMPUReq.py -i /home/arslan/stm32_discovery_arm_gcc/blinky/sizeinfo -l /home/arslan/stm32_discovery_arm_gcc/blinky/stm32_flash.overlay -c /home/arslan/stm32_discovery_arm_gcc/blinky/./autogen_data.c

verifF:
	./checkMPUReq.py -i ~/projects/LBC/FreeRTOS/FreeRTOS/Demo/CORTEX_M4F_STM32F407ZG-SK/sizeinfo -l ~/projects/LBC/FreeRTOS/FreeRTOS/Demo/CORTEX_M4F_STM32F407ZG-SK/./scripts/stm32_flash.overlay -c ~/projects/LBC/FreeRTOS/FreeRTOS/Demo/CORTEX_M4F_STM32F407ZG-SK/./autogen_data.c
