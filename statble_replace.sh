string_list=("cli\.array_info\[/cli\.array_data\["
             "cli\.volume_info\[/cli\.volume_data\["
	     "cli\.list_array/cli\.array_list"
	     "cli\.unmount_array/cli\.array_unmount")

file_names=("lib/*.py" "lib/*/*.py" "utils/*.py" "testcase/*.py" "testcase/*/*.py" "testcase/*/*/*.py")

for file_name in ${file_names[@]}
do
	for string in ${string_list[@]}
	do
		sed -i "s/$string/g" $file_name 
	done
done


